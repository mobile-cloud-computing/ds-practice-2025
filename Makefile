test_bookstore_post:
	curl 'http://localhost:8081/checkout' \
	  -H 'Accept: */*' \
	  -H 'Accept-Language: en-US,en;q=0.9' \
	  -H 'Cache-Control: no-cache' \
	  -H 'Connection: keep-alive' \
	  -H 'Content-Type: application/json' \
	  -H 'DNT: 1' \
	  -H 'Origin: http://localhost:8080' \
	  -H 'Pragma: no-cache' \
	  -H 'Referer: http://localhost:8080/' \
	  -H 'Sec-Fetch-Dest: empty' \
	  -H 'Sec-Fetch-Mode: cors' \
	  -H 'Sec-Fetch-Site: same-site' \
	  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36' \
	  -H 'sec-ch-ua: "Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"' \
	  -H 'sec-ch-ua-mobile: ?0' \
	  -H 'sec-ch-ua-platform: "macOS"' \
	  --data-raw '{"user":{"name":"John Doe","contact":"john.doe@example.ru"},"creditCard":{"number":"6011111111111117","expirationDate":"12/95","cvv":"123"},"userComment":"Please handle with care.","items":[{"name":"Book A","quantity":1},{"name":"Book B","quantity":2}],"billingAddress":{"street":"123 Main St","city":"Springfield","state":"IL","zip":"62701","country":"USA"},"shippingMethod":"Standard","giftWrapping":true,"termsAndConditionsAccepted":true}'
proto:
	python -m grpc_tools.protoc -I=utils/pb --python_out=utils/pb --grpc_python_out=utils/pb utils/pb/order_executor/order_executor.proto --proto_path=utils/pb --python_out=utils/pb --grpc_python_out=utils/pb
start:
	docker-compose up --build --scale order_executor=$(ORDER_EXECUTOR_REPLICAS)
