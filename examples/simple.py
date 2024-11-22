import openai
import os

url = os.environ["VLLM_SERVICE_URL"]

class Simple:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url=url,
            api_key="key"  # vLLM doesn't require a real key
        )
    
    def make_request(self):
        response = self.client.chat.completions.create(
            model="meta-llama/Llama-3.2-1B-Instruct",
            messages=[{"role": "user", "content": "Hello, how are you?"}]
        )
        return response.choices[0].message.content
    
if __name__ == "__main__":
    print(url)
    simple = Simple()
    print(simple.make_request())