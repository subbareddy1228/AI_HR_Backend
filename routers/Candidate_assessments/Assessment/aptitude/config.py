# app/config.py
import os

DATABASE_URL="postgresql://postgres:Admin@localhost:5432/signupdb"

# Email config
SENDER_EMAIL = "cheekatiabhinaya@gmail.com"
SENDER_PASSWORD = "wpje ppaq lcny xbod"

# OTP and Exam settings
OTP_EXPIRY = 300  # 5 minutes
EXAM_DURATION = 30*60  # 30 minutes
PASS_THRESHOLD = 30  # %
