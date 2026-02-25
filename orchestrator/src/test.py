import time
from google import genai

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

user_input = input("How can I help you? ")

start_time = time.time()

response = client.models.generate_content(
    model="gemini-2.5-flash-lite", contents=user_input
)

end_time = time.time()
response_time = end_time - start_time

print(response.text)
print(f"\nResponse time: {response_time:.2f} seconds")


