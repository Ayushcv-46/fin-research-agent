import os
import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

ipv4_client = httpx.Client(
    transport=httpx.HTTPTransport(local_address="0.0.0.0"),
    timeout=15.0,
)

llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    openai_api_key=os.getenv("NVIDIA_API_KEY"),
    openai_api_base="https://integrate.api.nvidia.com/v1",
    temperature=1, top_p=1, max_tokens=4096,
    http_client=ipv4_client, timeout=15.0, max_retries=0,
)

response = llm.invoke("Say hello in one sentence.")
print(response.content)