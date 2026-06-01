-- ============================================================================
-- SQL QUERIES TO INSERT PRASAD CHANDRAGIRI'S CANDIDATE DATA
-- ============================================================================
-- Resume: uploads/jd_files/prasad Chandragiri Resume.pdf
-- Extracted Date: October 30, 2025
-- ============================================================================

-- STEP 1: INSERT CANDIDATE INTO DATABASE
-- ============================================================================
INSERT INTO candidate (name, email, role, skills, stage, resume_url, notes, recruiter_comments)
VALUES (
    'Durga Sai Vara Prasad Chandragiri',
    'durgasaivaraprasadchan@gmail.com',
    'Full Stack Developer',
    'Java, JavaScript, HTML, CSS, MongoDB, Angular, ReactJs, MySQL, NodeJs, Spring Boot',
    'Applied',
    'uploads/jd_files/prasad Chandragiri Resume.pdf',
    'B.E in Mechanical Engineering from Vishnu Institute of Technology (2021). Certified Full Stack Developer Java by TalentSprint. Projects: Milkalicious (Angular, Spring Boot, MySQL) and Epic Eats (React.js, Node.js, Express.js, MongoDB). Phone: +91-9985614294',
    'Fresh graduate with full-stack experience. Strong in MERN and MEAN stacks. Good project portfolio.'
);

-- ============================================================================
-- STEP 2: VERIFY CANDIDATE INSERTION
-- ============================================================================
SELECT id, name, email, role, stage 
FROM candidate 
WHERE email = 'durgasaivaraprasadchan@gmail.com';

-- ============================================================================
-- STEP 3: VIEW AVAILABLE JOBS
-- ============================================================================
-- Check available jobs to assign the candidate to
SELECT id, title, department, employment_type, location, role, status
FROM job 
WHERE status IN ('Active', 'Open', 'Published')
ORDER BY created_at DESC;

-- ============================================================================
-- STEP 4: CREATE APPLICATION (ASSIGN CANDIDATE TO JOB)
-- ============================================================================
-- OPTION A: Direct insertion with known IDs
-- Replace <JOB_ID> with actual job ID from Step 3
INSERT INTO application (
    job_id, 
    candidate_id, 
    candidate_name, 
    candidate_email, 
    status, 
    created_at, 
    updated_at, 
    applied_at
)
VALUES (
    1,  -- <JOB_ID> - Replace with actual job_id
    (SELECT id FROM candidate WHERE email = 'durgasaivaraprasadchan@gmail.com'),
    'Durga Sai Vara Prasad Chandragiri',
    'durgasaivaraprasadchan@gmail.com',
    'applied',
    NOW(),
    NOW(),
    NOW()
);

-- ============================================================================
-- OPTION B: Assign to multiple jobs at once
-- ============================================================================
-- If you want to apply this candidate to multiple jobs simultaneously
INSERT INTO application (
    job_id, 
    candidate_id, 
    candidate_name, 
    candidate_email, 
    status, 
    created_at, 
    updated_at, 
    applied_at
)
SELECT 
    j.id,
    c.id,
    c.name,
    c.email,
    'applied',
    NOW(),
    NOW(),
    NOW()
FROM candidate c
CROSS JOIN job j
WHERE c.email = 'durgasaivaraprasadchan@gmail.com'
  AND j.id IN (1, 2, 3);  -- Replace with actual job IDs

-- ============================================================================
-- STEP 5: VERIFY APPLICATION CREATION
-- ============================================================================
SELECT 
    a.id AS application_id,
    a.candidate_name,
    a.candidate_email,
    j.title AS job_title,
    j.department,
    j.role AS job_role,
    a.status,
    a.applied_at
FROM application a
JOIN job j ON a.job_id = j.id
WHERE a.candidate_email = 'durgasaivaraprasadchan@gmail.com'
ORDER BY a.applied_at DESC;

-- ============================================================================
-- ALTERNATIVE: COMPLETE EXAMPLE WITH SPECIFIC JOB
-- ============================================================================
-- Example: If applying to a "Full Stack Developer" position (job_id = 5)

-- First, insert candidate (if not already exists)
INSERT INTO candidate (name, email, role, skills, stage, resume_url, notes, recruiter_comments)
SELECT 
    'Durga Sai Vara Prasad Chandragiri',
    'durgasaivaraprasadchan@gmail.com',
    'Full Stack Developer',
    'Java, JavaScript, HTML, CSS, MongoDB, Angular, ReactJs, MySQL, NodeJs, Spring Boot',
    'Applied',
    'uploads/jd_files/prasad Chandragiri Resume.pdf',
    'B.E in Mechanical Engineering. Certified Full Stack Developer. MERN/MEAN stack projects.',
    'Fresh graduate with strong technical foundation'
WHERE NOT EXISTS (
    SELECT 1 FROM candidate WHERE email = 'durgasaivaraprasadchan@gmail.com'
);

-- Then, create application
INSERT INTO application (
    job_id, 
    candidate_id, 
    candidate_name, 
    candidate_email, 
    status, 
    created_at, 
    updated_at, 
    applied_at
)
SELECT 
    5,  -- Replace with your job_id
    c.id,
    c.name,
    c.email,
    'applied',
    NOW(),
    NOW(),
    NOW()
FROM candidate c
WHERE c.email = 'durgasaivaraprasadchan@gmail.com'
  AND NOT EXISTS (
    SELECT 1 FROM application 
    WHERE candidate_id = c.id AND job_id = 5
  );

-- ============================================================================
-- USEFUL QUERIES FOR MANAGEMENT
-- ============================================================================

-- View all applications for this candidate
SELECT 
    c.name,
    c.email,
    j.title AS job_title,
    j.department,
    a.status,
    a.applied_at,
    a.updated_at
FROM candidate c
LEFT JOIN application a ON c.id = a.candidate_id
LEFT JOIN job j ON a.job_id = j.id
WHERE c.email = 'durgasaivaraprasadchan@gmail.com';

-- Update candidate stage
UPDATE candidate 
SET stage = 'Screening'  -- or 'Interview', 'Offer', etc.
WHERE email = 'durgasaivaraprasadchan@gmail.com';

-- Update application status
UPDATE application
SET status = 'pipeline',  -- or 'rejected', 'hired'
    updated_at = NOW()
WHERE candidate_email = 'durgasaivaraprasadchan@gmail.com'
  AND job_id = 1;  -- Replace with actual job_id

-- Add recruiter comments
UPDATE candidate
SET recruiter_comments = 'Strong technical skills in full-stack development. MERN and MEAN expertise. Good project portfolio with e-commerce applications.'
WHERE email = 'durgasaivaraprasadchan@gmail.com';

-- Delete application (if needed)
DELETE FROM application
WHERE candidate_email = 'durgasaivaraprasadchan@gmail.com'
  AND job_id = 1;  -- Replace with actual job_id

-- ============================================================================
-- CANDIDATE SUMMARY
-- ============================================================================
/*
Name: Durga Sai Vara Prasad Chandragiri
Email: durgasaivaraprasadchan@gmail.com
Phone: +91-9985614294
Education: B.E Mechanical Engineering (2021) - CGPA: 62%
Certification: Certified Full Stack Developer Java by TalentSprint

Technical Skills:
- Programming: Java, JavaScript
- Frontend: HTML, CSS, Angular, ReactJs
- Backend: NodeJs, Spring Boot
- Databases: MongoDB, MySQL

Projects:
1. Milkalicious - E-commerce milk products delivery
   Stack: Angular, Spring Boot, MySQL
   
2. Epic Eats - Online food delivery platform
   Stack: React.js, Node.js, Express.js, MongoDB
   Features: JWT authentication, password encryption, cart system

Soft Skills: Communication, Adaptability, Professionalism
LinkedIn: Available
GitHub: Available
LeetCode: Active

Ideal Roles: Full Stack Developer, MERN Stack Developer, MEAN Stack Developer,
            Java Full Stack Developer, Junior Software Engineer
*/

