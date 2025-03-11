import hashlib
from database.postgresdb import PostgresDB
import smtplib
from authorization.token_based import generate_access_token, generate_refresh_token, store_refresh_token

def send_email(subject, message, user_email):
    """Fake function gửi email"""
    email = "timenest.notif@gmail.com"
    receiver = user_email
    
    text = f"Subject: {subject}\n\n{message}"
    
    server = smtplib.SMTP("smtp.gmail.com",587)
    server.starttls()
    server.login(email, "xnlgyvyzzgyclnkh")
    server.sendmail(email,receiver,text)
    print("📨 Email have sent to " + receiver)
    # print(f"📨 Gửi email tới {user_email}: {subject} - {body}")

def hash_password(password):
    "Băm"
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username: str, password: str):
    hashed_password = hash_password(password)
    with PostgresDB() as db:
        user = db.select("users", {"username": username, "password": hashed_password})
    if user:
        print('TT DE GEN TOKEN:\n')
        print(user[0])
        data = {
            "userid": user[0]['userid'],
            "username":user[0]['username']
        }
        access_token = generate_access_token(data)
        refresh_token = generate_refresh_token(data)
        
        store_refresh_token(user[0]["userid"], refresh_token)
        
        return {
            "status_code": 200, 
            "info": data,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        } 
    return {"status_code": 400, "error": "Đéo xác thực được thằng lol này"}

def create_account(username: str, password: str, confirm_password: str, email: str = None, full_name: str = None):
    if password != confirm_password:
        return {"status_code": 400, "error": "❌ Mật khẩu xác nhận không khớp!"}

    hashed_password = hash_password(password)

    with PostgresDB() as db:
        try:
            user = db.insert("users", {
                "username": username,
                "email": email,
                "password": hashed_password,
                "full_name": full_name
            })
            return {"status_code": 200, "message": "✅ Tạo tài khoản thành công!", "user": user}
        except Exception as e:
            return {"status_code": 500, "error": f"❌ Lỗi: {e}"}
