import os
import torch
import random
import sqlite3
from datetime import datetime
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Set seed for reproducibility
random.seed(42)
torch.manual_seed(42)

# Create logs directory
os.makedirs("logs", exist_ok=True)

def load_logs():
    conn = sqlite3.connect("query_log.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT query, response FROM logs
        WHERE context IN ('semantic', 'lora', 'chatgpt')
    """)
    rows = cursor.fetchall()
    conn.close()
    return [f"Q: {q}\nA: {a}" for q, a in rows if q and a and len(q) > 8 and len(a) > 10]

def train():
    qa_texts = load_logs()
    if not qa_texts:
        print("❌ No Q&A pairs found. Aborting training.")
        return

    dataset = Dataset.from_dict({"text": qa_texts})
    tokenizer = AutoTokenizer.from_pretrained("tiiuae/falcon-rw-1b")

    def tokenize(example):
        return tokenizer(example["text"], truncation=True, padding="max_length", max_length=256)

    dataset = dataset.map(tokenize)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )

    model = AutoModelForCausalLM.from_pretrained(
        "tiiuae/falcon-rw-1b",
        quantization_config=bnb_config,
        device_map="auto"
    )
    model.gradient_checkpointing_enable()
    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["query_key_value"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, peft_config)

    run_id = datetime.now().strftime("run-%Y%m%d-%H%M%S")
    output_dir = os.path.join("tina-lora", run_id)
    os.makedirs(output_dir, exist_ok=True)

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        logging_dir="logs",
        num_train_epochs=3,
        learning_rate=2e-4,
        save_total_limit=2,
        save_steps=10,
        logging_steps=5,
        report_to="csv"  # Saves logs to CSV for review
    )

    trainer = Trainer(
        model=model,
        train_dataset=dataset,
        args=args,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False)
    )

    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"\u2705 Weekly fine-tuning complete. Model saved to '{output_dir}'")

if __name__ == "__main__":
    train()
