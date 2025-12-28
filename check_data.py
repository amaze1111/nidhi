from supabase import create_client, Client
from supabase_config import SUPABASE_URL, SUPABASE_KEY

def check_stored_data():
    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Get all records from the newsroom table
        result = supabase.table("newsroom").select("*").order('created_at', desc=True).execute()
        
        print("\nStored Search Data:")
        print("-" * 50)
        for record in result.data:
            print(f"Topic: {record['topic']}")
            print(f"Phone: {record['phone']}")
            print(f"Created at: {record['created_at']}")
            print("-" * 50)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_stored_data() 