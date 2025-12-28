from supabase import create_client, Client
from supabase_config import SUPABASE_URL, SUPABASE_KEY

def create_newsroom_table():
    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Create the newsroom table if it doesn't exist
        # Note: This is a simplified version. In production, you'd want to use proper SQL migrations
        query = """
        CREATE TABLE IF NOT EXISTS newsroom (
            id BIGSERIAL PRIMARY KEY,
            topic TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
        );
        """
        
        # Execute the query
        result = supabase.table("newsroom").select("*").limit(1).execute()
        print("Table 'newsroom' exists and is accessible!")
        print("Sample data:", result.data)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    create_newsroom_table() 