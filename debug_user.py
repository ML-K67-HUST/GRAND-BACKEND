import asyncio
from src.infrastructure.database.connection import db_manager
from sqlalchemy import text
from src.services.auth_service import AuthService

async def check_user():
    email = 'newuser@example.com'
    
    # Initialize database connection
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        # First, let's see what users exist
        query_all = text('SELECT email, created_at FROM users ORDER BY created_at DESC LIMIT 5')
        result_all = await session.execute(query_all)
        all_users = result_all.fetchall()
        
        print("Recent users in database:")
        for user_row in all_users:
            print(f"  - {user_row[0]} (created: {user_row[1]})")
        
        query = text('SELECT email, password_hash FROM users WHERE email = :email')
        result = await session.execute(query, {'email': email})
        row = result.fetchone()
        
        if row:
            print(f'Email: {row[0]}')
            print(f'Password hash length: {len(row[1])}')
            print(f'Password hash starts with: {row[1][:20]}...')
            print(f'Password hash type: {type(row[1])}')
            
            # Test password verification
            auth_service = AuthService()
            test_password = "password123"  # Use the password you tried to login with
            
            print(f'Testing password verification with: {test_password}')
            is_valid = auth_service.verify_password(test_password, row[1])
            print(f'Password verification result: {is_valid}')
            
            # Test with a known hash
            test_hash = auth_service.hash_password(test_password)
            print(f'New hash for same password: {test_hash[:20]}...')
            verify_new = auth_service.verify_password(test_password, test_hash)
            print(f'Verification of new hash: {verify_new}')
        else:
            print('User not found')

if __name__ == "__main__":
    asyncio.run(check_user()) 