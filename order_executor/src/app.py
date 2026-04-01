import os
import sys
import time
import grpc
import threading
from concurrent import futures

FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")

executor_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/order_executor")
)
queue_grpc_path = os.path.abspath(
    os.path.join(FILE, "../../../utils/pb/order_queue")
)

sys.path.insert(0, executor_grpc_path)
sys.path.insert(0, queue_grpc_path)

import order_executor_pb2 as executor_pb2
import order_executor_pb2_grpc as executor_grpc
import order_queue_pb2 as queue_pb2
import order_queue_pb2_grpc as queue_grpc


EXECUTOR_ID = int(os.getenv("EXECUTOR_ID", "1"))
EXECUTOR_PORT = os.getenv("EXECUTOR_PORT", "50055")
HEARTBEAT_INTERVAL = 2.0
LEADER_TIMEOUT = 5.0

state_lock = threading.Lock()
leader_id = None
last_heartbeat = time.time()
is_leader = False
election_in_progress = False


def parse_peers():
    peers = []
    raw = os.getenv("PEERS", "")
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        peer_id, peer_addr = item.split("@", 1)
        peers.append((int(peer_id), peer_addr))
    return peers


PEERS = parse_peers()


def has_fresh_leader_locked():
    if leader_id is None:
        return False
    if is_leader and leader_id == EXECUTOR_ID:
        return True
    return (time.time() - last_heartbeat) <= LEADER_TIMEOUT


def announce_coordinator():
    for pid, addr in PEERS:
        if pid == EXECUTOR_ID:
            continue
        send_rpc(
            addr,
            lambda stub: stub.Coordinator(
                executor_pb2.CoordinatorRequest(leader_id=EXECUTOR_ID),
                timeout=2.0,
            ),
        )


class ControlService(executor_grpc.OrderExecutorControlServicer):
    def Election(self, request, context):
        global election_in_progress

        if EXECUTOR_ID <= request.candidate_id:
            return executor_pb2.ElectionResponse(alive=False)

        print(f"[EXEC-{EXECUTOR_ID}] received election from {request.candidate_id}")

        with state_lock:
            already_leader = is_leader
            election_running = election_in_progress

        # If I am already the leader, just re-announce myself instead of
        # starting a brand new election.
        if already_leader:
            threading.Thread(target=announce_coordinator, daemon=True).start()
        elif not election_running:
            threading.Thread(target=start_election, daemon=True).start()

        return executor_pb2.ElectionResponse(alive=True)

    def Coordinator(self, request, context):
        global leader_id, is_leader, election_in_progress, last_heartbeat
        with state_lock:
            leader_id = request.leader_id
            is_leader = leader_id == EXECUTOR_ID
            election_in_progress = False
            last_heartbeat = time.time()

        print(f"[EXEC-{EXECUTOR_ID}] new leader is {leader_id}")
        return executor_pb2.Ack(ok=True)

    def Heartbeat(self, request, context):
        global leader_id, is_leader, last_heartbeat
        with state_lock:
            leader_id = request.leader_id
            is_leader = leader_id == EXECUTOR_ID
            last_heartbeat = time.time()
        return executor_pb2.Ack(ok=True)


def send_rpc(addr, fn):
    try:
        with grpc.insecure_channel(addr) as channel:
            stub = executor_grpc.OrderExecutorControlStub(channel)
            return fn(stub)
    except Exception:
        return None


def start_election():
    global election_in_progress, leader_id

    with state_lock:
        if election_in_progress:
            return

        # Do not start a new election if a healthy leader is already known.
        if has_fresh_leader_locked():
            return

        election_in_progress = True

    print(f"[EXEC-{EXECUTOR_ID}] starting election")

    higher_peers = [(pid, addr) for pid, addr in PEERS if pid > EXECUTOR_ID]
    got_answer = False

    for pid, addr in higher_peers:
        response = send_rpc(
            addr,
            lambda stub: stub.Election(
                executor_pb2.ElectionRequest(candidate_id=EXECUTOR_ID),
                timeout=2.0,
            ),
        )
        if response and response.alive:
            got_answer = True

    if not got_answer:
        become_leader()
        return

    # Wait for a higher node to announce a leader.
    time.sleep(LEADER_TIMEOUT)

    with state_lock:
        fresh_leader = has_fresh_leader_locked()
        election_in_progress = False

    if not fresh_leader:
        with state_lock:
            leader_id = None
        start_election()


def become_leader():
    global leader_id, is_leader, election_in_progress, last_heartbeat
    with state_lock:
        leader_id = EXECUTOR_ID
        is_leader = True
        election_in_progress = False
        last_heartbeat = time.time()

    print(f"[EXEC-{EXECUTOR_ID}] became leader")
    announce_coordinator()


def heartbeat_loop():
    while True:
        time.sleep(HEARTBEAT_INTERVAL)

        with state_lock:
            leader_now = is_leader

        if not leader_now:
            continue

        for pid, addr in PEERS:
            if pid == EXECUTOR_ID:
                continue
            send_rpc(
                addr,
                lambda stub: stub.Heartbeat(
                    executor_pb2.HeartbeatRequest(leader_id=EXECUTOR_ID),
                    timeout=2.0,
                ),
            )


def timeout_loop():
    global leader_id

    while True:
        time.sleep(1.0)

        with state_lock:
            if is_leader or election_in_progress:
                continue

            # During startup, if no leader is known yet, do not immediately
            # treat that as a timeout storm.
            if leader_id is None:
                continue

            expired = (time.time() - last_heartbeat) > LEADER_TIMEOUT

        if expired:
            print(f"[EXEC-{EXECUTOR_ID}] leader timeout detected")
            with state_lock:
                leader_id = None
            start_election()


def consume_loop():
    while True:
        time.sleep(1.0)

        with state_lock:
            if not is_leader:
                continue

        try:
            with grpc.insecure_channel("order_queue:50054") as channel:
                stub = queue_grpc.OrderQueueServiceStub(channel)
                response = stub.Dequeue(
                    queue_pb2.DequeueRequest(executor_id=str(EXECUTOR_ID)),
                    timeout=2.0,
                )
        except Exception as e:
            print(f"[EXEC-{EXECUTOR_ID}] queue error: {e}")
            continue

        if not response.success:
            continue

        print(
            f"[EXEC-{EXECUTOR_ID}] leader={EXECUTOR_ID} "
            f"executing order={response.order.order_id} "
            f'user="{response.order.user_name}" item_count={response.order.item_count}'
        )
        print("Order is being executed...")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    executor_grpc.add_OrderExecutorControlServicer_to_server(
        ControlService(), server
    )
    server.add_insecure_port("[::]:" + EXECUTOR_PORT)
    server.start()
    print(f"[EXEC-{EXECUTOR_ID}] listening on port {EXECUTOR_PORT}")

    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=timeout_loop, daemon=True).start()
    threading.Thread(target=consume_loop, daemon=True).start()

    # Give peers a brief moment to come up, then start election only if
    # no leader is already known.
    time.sleep(1.0)
    with state_lock:
        should_start = (leader_id is None) and (not election_in_progress)

    if should_start:
        start_election()

    server.wait_for_termination()


if __name__ == "__main__":
    serve()