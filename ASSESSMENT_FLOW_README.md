<!-- # 🔄 Sequential Assessment Flow - Implementation Guide

## Overview
This document describes the **automated sequential assessment flow** where candidates automatically receive the next assessment link when they pass the current one.

---

## 📊 Assessment Flow Architecture

### **Flow Diagram:**

Recruiter Creates Assessments in Library
                ↓
Recruiter Assigns ONLY Aptitude Test
                ↓
        Candidate Takes Aptitude
                ↓
        ┌───────┴───────┐
        ↓               ↓
    QUALIFIED        REJECTED
        ↓               ↓
Auto-send         Send Rejection
Communication      Email (Flow Stops)
Link
        ↓
Candidate Takes Communication
        ↓
        ┌───────┴───────┐
        ↓               ↓
    QUALIFIED        REJECTED
        ↓               ↓
Auto-send          Send Rejection
Coding Link        Email (Flow Stops)
        ↓
Candidate Takes Coding
        ↓
        ┌───────┴───────┐
        ↓               ↓
    QUALIFIED        REJECTED
        ↓               ↓
Auto-send         Send Rejection
Interview         Email (Flow Stops)
Scheduling Link
```

---

## 🎯 Implementation Details

### 1. **Aptitude Test** (`Backend/routers/Candidate_assessments/Assessment/aptitude/routers/exam.py`)

**Submission Logic (Line 115-219):**
- Scores the test (15/25 required to pass)
- Updates status: `"Qualified"` or `"Regret"`
- Marks assignment as `"Completed"` in database
- **If Qualified:** Automatically sends email with Communication test link
- **If Rejected:** Sends rejection email

**Email Content (Qualified):**
```
Subject: ✅ Aptitude Test Passed - Next: Communication Assessment

Dear [Candidate Name],

🎉 Congratulations! You have successfully passed the Aptitude Test 
with a score of [X]/25.

You are now invited to take the next stage of our assessment:

📢 Communication Assessment
🔗 Test Link: [Auto-generated link]

Instructions:
1. Click on the link above to start your communication assessment
2. You will receive an OTP for verification
3. The test includes Reading, Writing, and Listening sections
4. Complete the test in one sitting

### 2. **Communication Test** (`Backend/routers/Candidate_assessments/Assessment/communication/comm_routes.py`)

**Submission Logic (Line 134-249):**
- Scores Writing (10 pts), Listening (5 pts), MCQs (5 pts) = 20 total
- Pass threshold: 9/20 points
- Updates status: `passed = true/false`
- Marks assignment as `"Completed"` in database
- **If Qualified:** Automatically sends email with Coding test link
- **If Rejected:** Sends rejection email

**Email Content (Qualified):**

Subject: ✅ Communication Test Passed - Next: Coding Assessment

Dear [Candidate Name],

🎉 Congratulations! You have successfully passed the Communication 
Assessment with a score of [X]/[Y].

You are now invited to take the final stage of our technical assessment:

💻 Coding Assessment
🔗 Test Link: [Auto-generated link]

Instructions:
1. Click on the link above to start your coding assessment
2. You will receive an OTP for verification
3. You can write code in Python, C++, or Java
4. Complete and test your solutions thoroughly
```

---

### 3. **Coding Test** (`Backend/routers/Candidate_assessments/Assessment/coding/coding.py`)

**Finalization Logic (Line 118-236):**
- Counts successful code submissions
- Pass threshold: At least 1 successful submission
- Marks assignment as `"Completed"` in database
- **If Qualified:** Automatically sends email with Interview scheduling link
- **If Rejected:** Sends rejection email

**Email Content (Qualified):**
```
Subject: ✅ Coding Test Passed - Interview Scheduling

Dear [Candidate Name],

🎉 Congratulations! You have successfully completed the Coding 
Assessment with [X] successful submission(s).

You have qualified for the next stage - Interview Round!

📅 Interview Scheduling
🔗 Schedule Link: [Auto-generated link]

Instructions:
1. Click on the link above to schedule your interview
2. Choose a convenient time slot
3. You will receive a confirmation email with meeting details
4. Prepare to discuss your technical skills and experience
```

---

## 🛠️ Database Configuration

### **Fixed Issues:**
1. **Coding Module Database Connection:**
   - **Problem:** Coding module was trying to load DB credentials from `.env` file
   - **Solution:** Updated `Backend/routers/Candidate_assessments/Assessment/coding/config.py` to import credentials from `core/database.py`
   - **Credentials:** `postgres:4649@localhost:5432/db`

2. **Assignment Status Tracking:**
   - Each assessment completion updates the `Assignment` table
   - Status changes: `"Pending"` → `"In Progress"` → `"Completed"`
   - Results stored in respective tables:
     - Aptitude: `aptitude_assessment_results` table
     - Communication: `communication_assessment_results` table
     - Coding: `coding_assessment_results` table

---

## 📧 Email Configuration

### **Email Function Locations:**
- **Aptitude:** `Backend/routers/Candidate_assessments/Assessment/aptitude/utils.py` → `send_email()`
- **Communication:** `Backend/routers/Candidate_assessments/Assessment/communication/utils_comm.py` → `send_email()`
- **Coding:** `Backend/routers/Candidate_assessments/Assessment/coding/utils.py` → `send_email()`

### **Frontend Base URL:**
- **Environment Variable:** `FRONTEND_URL` (defaults to `http://localhost:5173`)
- **Usage:** Auto-generates assessment links in emails

---

## 🎬 How Recruiters Use This System

### **Step 1: Create Assessments in Library**
1. Go to **Assessment Library**
2. Create assessments for each type:
   - Aptitude (25 questions, Medium level)
   - Communication (Reading, Writing, Listening)
   - Coding (2-3 coding problems)

### **Step 2: Assign ONLY Aptitude Test**
1. Go to **Assign Assessments**
2. Select candidate(s)
3. **Assign ONLY the Aptitude assessment** (not all three!)
4. Check "Send Email" option
5. Submit

### **Step 3: Automated Flow Takes Over**
- Candidate receives Aptitude test email
- After passing Aptitude → **System auto-sends Communication link**
- After passing Communication → **System auto-sends Coding link**
- After passing Coding → **System auto-sends Interview link**

### **Step 4: Monitor Progress**
1. Go to **Assignment Status** page
2. View real-time status:
   - Assignment Status: `Pending` / `In Progress` / `Completed`
   - Test Result: `Qualified` / `Regret`
   - Score: Displayed for each assessment
3. Click **"View Details"** for comprehensive information

---

## 📋 Testing the Complete Flow

### **Test Scenario:**

1. **Create Aptitude Assessment:**
   - Type: Aptitude
   - Difficulty: Medium
   - Questions: 25

2. **Assign to Test Candidate:**
   - Email: `test@example.com`
   - Send email with aptitude link

3. **Complete Aptitude Test:**
   - Take test and score ≥15/25
   - ✅ Receive email with Communication link automatically

4. **Complete Communication Test:**
   - Take test and score ≥9/20
   - ✅ Receive email with Coding link automatically

5. **Complete Coding Test:**
   - Submit at least 1 successful solution
   - ✅ Receive email with Interview scheduling link automatically

6. **Check Assignment Status:**
   - All three assignments show as `"Completed"`
   - Each shows `"Qualified"` or `"Regret"` status
   - Scores displayed for each test

---

## 🔧 Configuration Files Modified

### **Files Changed:**
1. `Backend/routers/Candidate_assessments/Assessment/aptitude/routers/exam.py`
   - Added sequential flow logic to `submit_exam()` (Line 142-219)
   - Sends Communication link on qualification

2. `Backend/routers/Candidate_assessments/Assessment/communication/comm_routes.py`
   - Added sequential flow logic to `submit_answers()` (Line 172-249)
   - Sends Coding link on qualification

3. `Backend/routers/Candidate_assessments/Assessment/coding/coding.py`
   - Updated `finalize()` with sequential flow (Line 132-236)
   - Sends Interview link on qualification

4. `Backend/routers/Candidate_assessments/Assessment/coding/config.py`
   - Fixed database connection to use main app credentials
   - Resolved `"no password supplied"` error

5. `Backend/routers/Candidate_assessments/Assessment/Assessments/services/assignment_service.py`
   - Enhanced status tracking with `test_status` field
   - Shows `"Qualified"` / `"Regret"` in results

6. `client/src/components/assessments/AssessmentResults.jsx`
   - Added "View Details" modal
   - Displays comprehensive assignment information
   - Shows score and test result badges

---

## ✅ Benefits of This Approach

1. **Automated Workflow:** No manual intervention needed after initial assignment
2. **Better Candidate Experience:** Clear progression through assessment stages
3. **Reduced Administrative Overhead:** Recruiter only assigns first test
4. **Real-time Tracking:** Complete visibility in Assignment Status page
5. **Consistent Communication:** Standardized, professional emails at each stage
6. **Fail-Fast:** Rejected candidates don't proceed to next stages

---

## 🚀 Future Enhancements

### **Potential Additions:**
1. **Configurable Pass Thresholds:** Allow recruiters to set custom passing scores
2. **Assessment Scheduling:** Add due dates for each assessment stage
3. **Reminder Emails:** Automated reminders for pending assessments
4. **Analytics Dashboard:** Track completion rates and average scores
5. **Custom Email Templates:** Allow recruiters to customize email content
6. **Multi-language Support:** Emails in candidate's preferred language

---

## 📞 Support

For issues or questions about the assessment flow:
1. Check backend logs for email sending status
2. Verify database credentials in `Backend/core/database.py`
3. Ensure email service is configured properly
4. Check `Assignment` and `Assessment` tables for data consistency

--- -->
