
-- INSERT SAMPLE CANDIDATES AND APPLICATIONS
-- AI Recruitment Platform


-- Step 1: Check your job IDs first
SELECT id, title, department, status FROM job WHERE recruiter_id = 4;


-- Step 2: Insert 10 Sample Candidates


INSERT INTO candidate (name, email, role, skills, stage, resume_url, notes, recruiter_comments) 
VALUES
-- Engineering Candidates
('John Smith', 'john.smith@email.com', 'Senior Software Engineer', 'JavaScript, React, Node.js, Python, AWS, Docker', 'Applied', 'https://example.com/resumes/john-smith.pdf', '5 years of experience in full-stack development. Strong problem-solving skills and leadership experience.', NULL),

('Sarah Johnson', 'sarah.johnson@email.com', 'Frontend Developer', 'React, TypeScript, CSS, HTML, JavaScript, Redux', 'Applied', 'https://example.com/resumes/sarah-johnson.pdf', '3 years of experience. Expert in React and modern frontend frameworks. Portfolio available.', NULL),

('Michael Chen', 'michael.chen@email.com', 'Backend Developer', 'Python, Django, PostgreSQL, Redis, AWS, Microservices', 'Applied', 'https://example.com/resumes/michael-chen.pdf', '4 years of experience. Specialized in scalable backend systems and API design.', NULL),

('Emily Rodriguez', 'emily.rodriguez@email.com', 'Full Stack Developer', 'JavaScript, React, Node.js, MongoDB, Express, GraphQL', 'Applied', 'https://example.com/resumes/emily-rodriguez.pdf', '6 years of experience. Full-stack expertise with MERN stack and cloud deployment.', NULL),

('David Kumar', 'david.kumar@email.com', 'DevOps Engineer', 'Docker, Kubernetes, AWS, Jenkins, Terraform, CI/CD', 'Applied', 'https://example.com/resumes/david-kumar.pdf', '7 years of experience. Expert in cloud infrastructure, automation, and monitoring.', NULL),

-- Design & Product
('Lisa Wang', 'lisa.wang@email.com', 'UI/UX Designer', 'Figma, Adobe XD, Sketch, User Research, Prototyping, Wireframing', 'Applied', 'https://example.com/resumes/lisa-wang.pdf', '4 years of experience. Strong portfolio in mobile and web design. User-centered approach.', NULL),

-- Data & Analytics
('Robert Taylor', 'robert.taylor@email.com', 'Data Scientist', 'Python, Machine Learning, TensorFlow, Pandas, SQL, Statistics', 'Applied', 'https://example.com/resumes/robert-taylor.pdf', '5 years of experience. PhD in Computer Science. Machine learning and AI expertise.', NULL),

-- QA & Testing
('Priya Sharma', 'priya.sharma@email.com', 'QA Engineer', 'Selenium, Jest, Cypress, API Testing, Automation, Pytest', 'Applied', 'https://example.com/resumes/priya-sharma.pdf', '3 years of experience. Automation testing specialist. ISTQB certified.', NULL),

-- Product Management
('James Wilson', 'james.wilson@email.com', 'Product Manager', 'Agile, Scrum, JIRA, Product Strategy, Roadmapping, Stakeholder Management', 'Applied', 'https://example.com/resumes/james-wilson.pdf', '8 years of experience. Led multiple successful product launches. MBA from top university.', NULL),

-- Mobile Development
('Aisha Patel', 'aisha.patel@email.com', 'Mobile Developer', 'React Native, iOS, Android, Swift, Kotlin, Flutter', 'Applied', 'https://example.com/resumes/aisha-patel.pdf', '4 years of experience. Published apps with 1M+ downloads. Cross-platform expertise.', NULL);

-- Verify candidates inserted
SELECT id, name, email, role, stage FROM candidate ORDER BY id DESC LIMIT 10;


-- Step 3: Create Applications 
-- (Candidates apply to your job)


-- IMPORTANT: Replace job_id = 1 with your actual job ID from Step 1!

-- Get candidate IDs (they should be auto-incremented)
SELECT id, name, email FROM candidate ORDER BY id DESC LIMIT 10;

-- Apply first 7 candidates to job ID 1 (Replace 1 with YOUR job ID)
INSERT INTO application (job_id, candidate_id, candidate_name, candidate_email, status, created_at, updated_at, applied_at) 
VALUES
-- Apply to MERN Stack Developer job (or your job)
(2, (SELECT id FROM candidate WHERE email = 'john.smith@email.com'), 'John Smith', 'john.smith@email.com', 'applied', NOW(), NOW(), NOW()),
(2, (SELECT id FROM candidate WHERE email = 'sarah.johnson@email.com'), 'Sarah Johnson', 'sarah.johnson@email.com', 'applied', NOW(), NOW(), NOW()),
(2, (SELECT id FROM candidate WHERE email = 'michael.chen@email.com'), 'Michael Chen', 'michael.chen@email.com', 'applied', NOW(), NOW(), NOW()),
(2, (SELECT id FROM candidate WHERE email = 'emily.rodriguez@email.com'), 'Emily Rodriguez', 'emily.rodriguez@email.com', 'applied', NOW(), NOW(), NOW()),
(2, (SELECT id FROM candidate WHERE email = 'david.kumar@email.com'), 'David Kumar', 'david.kumar@email.com', 'applied', NOW(), NOW(), NOW()),
(2, (SELECT id FROM candidate WHERE email = 'priya.sharma@email.com'), 'Priya Sharma', 'priya.sharma@email.com', 'applied', NOW(), NOW(), NOW()),
(2, (SELECT id FROM candidate WHERE email = 'aisha.patel@email.com'), 'Aisha Patel', 'aisha.patel@email.com', 'applied', NOW(), NOW(), NOW());


-- Step 4: Verify Data


-- View all candidates
SELECT id, name, email, role, skills FROM candidate;

-- View all applications with job details
SELECT 
  a.id as application_id,
  j.title as job_title,
  c.name as candidate_name,
  c.email as candidate_email,
  c.role,
  c.skills,
  a.status,
  a.applied_at
FROM application a
JOIN candidate c ON a.candidate_id = c.id
JOIN job j ON a.job_id = j.id
WHERE j.recruiter_id = 4
ORDER BY a.applied_at DESC;

-- Count applications per job
SELECT 
  j.id,
  j.title,
  COUNT(a.id) as total_applications
FROM job j
LEFT JOIN application a ON j.id = a.job_id
WHERE j.recruiter_id = 4
GROUP BY j.id, j.title
ORDER BY j.id;


-- Additional Sample Data (Optional)


-- If you want more candidates:
INSERT INTO candidate (name, email, role, skills, stage, resume_url, notes, recruiter_comments) 
VALUES
('Alex Thompson', 'alex.thompson@email.com', 'Cloud Architect', 'AWS, Azure, GCP, Architecture, Security, Scalability', 'Applied', 'https://example.com/resumes/alex-thompson.pdf', '10 years of experience. AWS Solutions Architect certified.', NULL),
('Maria Garcia', 'maria.garcia@email.com', 'Scrum Master', 'Agile, Scrum, Kanban, Team Management, Sprint Planning', 'Applied', 'https://example.com/resumes/maria-garcia.pdf', '6 years of experience. CSM and PSM certified.', NULL),
('Kevin Lee', 'kevin.lee@email.com', 'Security Engineer', 'Cybersecurity, Penetration Testing, OWASP, Security Audits', 'Applied', 'https://example.com/resumes/kevin-lee.pdf', '5 years of experience. CEH and CISSP certified.', NULL),
('Nina Desai', 'nina.desai@email.com', 'Business Analyst', 'Requirements Analysis, SQL, Tableau, Process Improvement', 'Applied', 'https://example.com/resumes/nina-desai.pdf', '4 years of experience. Strong analytical and communication skills.', NULL),
('Tom Anderson', 'tom.anderson@email.com', 'Marketing Manager', 'Digital Marketing, SEO, SEM, Content Strategy, Analytics', 'Applied', 'https://example.com/resumes/tom-anderson.pdf', '7 years of experience. Led campaigns with 300% ROI increase.', NULL);


-- DONE!


-- Final verification query:
SELECT 
  'Candidates' as type, 
  COUNT(*) as count 
FROM candidate
UNION ALL
SELECT 
  'Applications' as type, 
  COUNT(*) as count 
FROM application;

