
  Flipwise

Flipwise is an AI-powered study buddy created by **Edugenie Labs**, owned by **Mathengeisaac**.
It helps students convert their notes into smart flashcards for efficient revision.

---

## 🚀 Features

* Secure user authentication with JWT & Flask-Bcrypt
* Free and Premium accounts with different access levels
* Flashcard generation for quick study sessions
* Simple Flask + MySQL backend

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/flipwise.git
cd flipwise
```

### 2. Create a Virtual Environment & Install Dependencies

```bash
python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows

pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=flipwise
HF_API_KEY=your_huggingface_api_key
```

---

## 🗄️ Database Setup

### 1. Create Database & Users Table

Run in MySQL Workbench:

```sql
CREATE DATABASE flipwise;
USE flipwise;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_premium BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Insert Test Accounts

Passwords are hashed with **bcrypt**, so they work with login.

```sql
-- Free account
INSERT INTO users (name, email, password, is_premium, created_at)
VALUES ('Free User', 'free@example.com', '$2b$12$3Gp1qgH8B0Vs3o1Gd9g4SO3a1f53LrM6At3EnN59mK2A2oBcLqFne', 0, NOW());

-- Premium account
INSERT INTO users (name, email, password, is_premium, created_at)
VALUES ('Premium User', 'premium@example.com', '$2b$12$3Gp1qgH8B0Vs3o1Gd9g4SO3a1f53LrM6At3EnN59mK2A2oBcLqFne', 1, NOW());
```

✅ Both accounts use the password: **1234**

---

## 🧪 Testing Login

Run the Flask app and test:

* **Free Account** → email: `free@example.com` | password: `1234`
* **Premium Account** → email: `premium@example.com` | password: `1234`

The working link for my website on render is https://flipwise-8nrs.onrender.com
