from transformers import AutoProcessor, AutoModelForCausalLM

MODEL_NAME = "microsoft/Florence-2-base"

print("Loading Florence-2 processor...")

processor = AutoProcessor.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

print("Loading Florence-2 model...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

print("Florence-2 loaded successfully!")