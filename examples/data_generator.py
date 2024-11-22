import openai
import pandas as pd
import json
from typing import List, Dict
import os
import random

class HealthProductDataGenerator:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url= os.environ["VLLM_SERVICE_URL"],
            api_key="dummy"  # vLLM doesn't require a real key
        )
        
    def _clean_and_parse_json(self, text: str) -> dict:
        """Clean the response and extract JSON."""
        # Remove any markdown formatting
        text = text.replace("```json", "").replace("```", "")
        # Remove any natural language before or after the JSON
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # If direct parsing fails, try to find JSON-like content
            import re
            json_pattern = r'\[.*\]'
            match = re.search(json_pattern, text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Could not parse JSON from response: {text[:200]}...")

    def generate_users(self, n_users: int = 100) -> pd.DataFrame:
        users = []
        batch_size = 10
        
        for i in range(0, n_users, batch_size):
            current_batch_size = min(batch_size, n_users - i)
            prompt = f"""You are a JSON generator. Generate exactly {current_batch_size} users for a health supplement store.
            Return ONLY a JSON array of objects, each with these exact fields:
            - user_id (string starting with U followed by a number, e.g., U001, you are currently on U00{i+1})
            - user_fname (string)
            - user_lname (string)
            - loyalty_reward_member (boolean)
            
            Return ONLY the JSON array with no additional text or formatting."""
            try:
                response = self.client.chat.completions.create(
                    model="meta-llama/Llama-3.2-1B-Instruct",
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }],
                    max_tokens=1000,
                    temperature=0.7
                )
                
                batch_users = self._clean_and_parse_json(response.choices[0].message.content)
                users.extend(batch_users)
                print(f"Generated {len(batch_users)} users in batch {i//batch_size + 1}")
            except Exception as e:
                print(f"Error in batch {i//batch_size + 1}: {str(e)}")
                continue
                
        return pd.DataFrame(users)

    def generate_products(self, n_products: int = 1000) -> pd.DataFrame:
        products = []
        batch_size = 10
        
        for i in range(0, n_products, batch_size):
            current_batch_size = min(batch_size, n_products - i)
            prompt = f"""You are a JSON generator. Generate exactly {current_batch_size} health supplement products.
            Return ONLY a JSON array of objects, each with these exact fields:
            - product_id (string starting with P followed by a number, e.g., P001, you are currently on P00{i+1})
            - product_name (string)
            - product_brand (string)
            - active_ingredients (list of strings, max 5 ingredients)
            
            Include realistic combinations like:
            - Protein powder with creatine, BCAAs
            - Weight loss supplements with metabolism boosters
            - Joint health products with glucosamine, collagen
            
            Return ONLY the JSON array with no additional text or formatting."""
            
            try:
                response = self.client.chat.completions.create(
                    model="meta-llama/Llama-3.2-1B-Instruct",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                batch_products = self._clean_and_parse_json(response.choices[0].message.content)
                products.extend(batch_products)
                print(f"Generated {len(batch_products)} products in batch {i//batch_size + 1}")
            except Exception as e:
                print(f"Error in batch {i//batch_size + 1}: {str(e)}")
                continue
                
        return pd.DataFrame(products)

    def generate_transactions(self, 
                            users_df: pd.DataFrame, 
                            products_df: pd.DataFrame, 
                            n_transactions: int = 2000) -> pd.DataFrame:
        transactions = []
        batch_size = 10
        
        # Get all available IDs
        all_user_ids = users_df['user_id'].tolist()
        all_product_ids = products_df['product_id'].tolist()

        for i in range(0, n_transactions, batch_size):
            current_batch_size = min(batch_size, n_transactions - i)
            
            # Randomly sample IDs for this batch
            sample_users = random.sample(all_user_ids, min(batch_size, len(all_user_ids)))
            sample_products = random.sample(all_product_ids, min(batch_size, len(all_product_ids)))
            
            prompt = f"""You are a JSON generator. Generate exactly {current_batch_size} supplement purchase transactions.
            Return ONLY a JSON array of objects, each with these fields:
            - user_id (string, must be from provided list)
            - product_id (string, must be from provided list)
            
            Rules:
            1. Users often buy complementary products together
            2. Loyalty members make more purchases
            3. Create clear patterns of supplement stacks
            
            Use ONLY these user_ids: {json.dumps(sample_users)}
            Use ONLY these product_ids: {json.dumps(sample_products)}
            
            Return ONLY the JSON array with no additional text or formatting."""
        
            try:
                response = self.client.chat.completions.create(
                    model="meta-llama/Llama-3.2-1B-Instruct",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1500,
                    temperature=0.7
                )
                
                batch_transactions = self._clean_and_parse_json(response.choices[0].message.content)
                
                # Validate that generated IDs are from the provided lists
                valid_transactions = [
                    t for t in batch_transactions 
                    if t['user_id'] in sample_users and t['product_id'] in sample_products  # Note: changed to check against sample lists
                ]
                
                transactions.extend(valid_transactions)
                print(f"Generated {len(valid_transactions)} valid transactions in batch {i//batch_size + 1}")
            except Exception as e:
                print(f"Error in batch {i//batch_size + 1}: {str(e)}")
                continue
                
        return pd.DataFrame(transactions)

# Usage example
if __name__ == "__main__":
    generator = HealthProductDataGenerator()
    
    # Generate datasets
    users_df = generator.generate_users(n_users=100)
    products_df = generator.generate_products(n_products=1000)
    transactions_df = generator.generate_transactions(users_df, products_df, n_transactions=10000)

    if not os.path.exists("data"):
        os.makedirs("data") 
        
    # Save to CSV
    users_df.to_csv("data/users.csv", index=False)
    products_df.to_csv("data/products.csv", index=False)
    transactions_df.to_csv("data/transactions.csv", index=False) 

