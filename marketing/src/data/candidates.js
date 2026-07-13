// 50 fictional enterprise candidate profiles for AlphaSource AI's Guided
// Demo Mode (Sprint 6, Task 3/8). All names, employment histories, and
// project descriptions are synthetic -- generated programmatically, not
// copied from real people or real LinkedIn profiles. Company names are
// used only as realistic employer context (Google, Microsoft, Amazon,
// Flipkart, Swiggy, PhonePe, Atlassian, Freshworks, Meesho, Razorpay,
// Zoho, Adobe, Salesforce, Oracle, IBM, Infosys, TCS, Accenture), the
// same way a design mockup uses real brand names as placeholder context.
//
// This file is used exclusively by Guided Demo Mode (deterministic,
// offline, cannot fail during a live presentation) -- it is NOT wired
// into the real backend's candidate_repository seed data, per Sprint 6's
// explicit instruction not to modify the search pipeline or backend.
export const DEMO_CANDIDATES = [
  {
    "id": "cand-001",
    "name": "Aditya Sharma",
    "role": "Backend Engineer",
    "experience": 5.1,
    "skills": [
      "Spring Boot",
      "Java",
      "Kafka",
      "Kubernetes",
      "Docker"
    ],
    "location": "Bangalore",
    "current_company": "Google",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Bombay",
      "year": 2018
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Google",
        "title": "Backend Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Flipkart",
        "title": "Backend Engineer",
        "start": 2023,
        "end": 2024,
        "current": false
      },
      {
        "company": "IBM",
        "title": "Backend Engineer",
        "start": 2021,
        "end": 2023,
        "current": false
      }
    ],
    "projects": [
      "Owned the payments reconciliation pipeline processing 50M+ transactions per day.",
      "Led a team of 5 engineers building the company's first multi-region deployment."
    ],
    "certifications": [
      "PMP",
      "Azure Solutions Architect Expert"
    ],
    "languages": [
      "English",
      "Kannada"
    ]
  },
  {
    "id": "cand-002",
    "name": "Ananya Kapoor",
    "role": "Product Engineer",
    "experience": 3.7,
    "skills": [
      "React",
      "System Design",
      "Kubernetes",
      "TypeScript",
      "Node.js"
    ],
    "location": "Hyderabad",
    "current_company": "Microsoft",
    "source": "Referral",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Delhi",
      "year": 2020
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "Microsoft",
        "title": "Product Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Swiggy",
        "title": "Product Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      }
    ],
    "projects": [
      "Led migration of 50 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 35%.",
      "Built a real-time recommendation engine serving 12M+ daily active users with sub-100ms latency.",
      "Built an ML-based fraud detection system reducing false positives by 40%."
    ],
    "certifications": [
      "Google Cloud Professional ML Engineer"
    ],
    "languages": [
      "English",
      "Hindi"
    ]
  },
  {
    "id": "cand-003",
    "name": "Rohan Pillai",
    "role": "Data Scientist",
    "experience": 6.9,
    "skills": [
      "NLP",
      "TensorFlow",
      "Python",
      "Machine Learning",
      "Pandas"
    ],
    "location": "Pune",
    "current_company": "Amazon",
    "source": "AlphaSource Network",
    "education": {
      "degree": "B.Tech Information Technology",
      "school": "NIT Trichy",
      "year": 2017
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "Amazon",
        "title": "Senior Data Scientist",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Salesforce",
        "title": "Data Scientist",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Atlassian",
        "title": "Data Scientist",
        "start": 2020,
        "end": 2022,
        "current": false
      }
    ],
    "projects": [
      "Designed and shipped an internal search platform reducing on-call incident triage time by 45%.",
      "Owned the payments reconciliation pipeline processing 5M+ transactions per day."
    ],
    "certifications": [
      "PMP"
    ],
    "languages": [
      "English",
      "Bengali"
    ]
  },
  {
    "id": "cand-004",
    "name": "Priya Kaur",
    "role": "DevOps Engineer",
    "experience": 7.1,
    "skills": [
      "Prometheus",
      "AWS",
      "Terraform",
      "Ansible",
      "Docker"
    ],
    "location": "Gurgaon",
    "current_company": "Flipkart",
    "source": "Career Site",
    "education": {
      "degree": "B.E Computer Science",
      "school": "BITS Pilani",
      "year": 2016
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Flipkart",
        "title": "Senior DevOps Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Freshworks",
        "title": "DevOps Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Adobe",
        "title": "DevOps Engineer",
        "start": 2019,
        "end": 2022,
        "current": false
      }
    ],
    "projects": [
      "Designed and shipped an internal search platform reducing on-call incident triage time by 22%.",
      "Owned the payments reconciliation pipeline processing 50M+ transactions per day.",
      "Built an ML-based fraud detection system reducing false positives by 40%."
    ],
    "certifications": [
      "Azure Solutions Architect Expert"
    ],
    "languages": [
      "English",
      "Kannada",
      "Bengali"
    ]
  },
  {
    "id": "cand-005",
    "name": "Karan Trivedi",
    "role": "Frontend Engineer",
    "experience": 11.6,
    "skills": [
      "React",
      "Webpack",
      "Redux",
      "Tailwind CSS",
      "Next.js"
    ],
    "location": "Chennai",
    "current_company": "Swiggy",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Electronics",
      "school": "IIT Madras",
      "year": 2012
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "Swiggy",
        "title": "Senior Frontend Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Amazon",
        "title": "Frontend Engineer",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "Oracle",
        "title": "Frontend Engineer",
        "start": 2019,
        "end": 2021,
        "current": false
      },
      {
        "company": "Freshworks",
        "title": "Frontend Engineer",
        "start": 2016,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Built a real-time recommendation engine serving 50M+ daily active users with sub-100ms latency.",
      "Built an ML-based fraud detection system reducing false positives by 30%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Telugu",
      "Kannada"
    ]
  },
  {
    "id": "cand-006",
    "name": "Sneha Krishnan",
    "role": "Platform Engineer",
    "experience": 13.0,
    "skills": [
      "Kubernetes",
      "Go",
      "EKS",
      "AWS",
      "Terraform"
    ],
    "location": "Mumbai",
    "current_company": "PhonePe",
    "source": "LinkedIn",
    "education": {
      "degree": "M.Tech Computer Science",
      "school": "IISc Bangalore",
      "year": 2010
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "PhonePe",
        "title": "Senior Platform Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Accenture",
        "title": "Platform Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Freshworks",
        "title": "Platform Engineer",
        "start": 2019,
        "end": 2022,
        "current": false
      },
      {
        "company": "Amazon",
        "title": "Platform Engineer",
        "start": 2015,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Re-architected the checkout flow, improving conversion by 18%.",
      "Built a real-time recommendation engine serving 8M+ daily active users with sub-100ms latency."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Kannada"
    ]
  },
  {
    "id": "cand-007",
    "name": "Arjun Iyer",
    "role": "Machine Learning Engineer",
    "experience": 11.3,
    "skills": [
      "Python",
      "NLP",
      "AWS SageMaker",
      "Computer Vision",
      "MLOps"
    ],
    "location": "Noida",
    "current_company": "Atlassian",
    "source": "LinkedIn",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "VIT Vellore",
      "year": 2012
    },
    "notice_period": "15 days",
    "timeline": [
      {
        "company": "Atlassian",
        "title": "Senior Machine Learning Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "TCS",
        "title": "Machine Learning Engineer",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "PhonePe",
        "title": "Machine Learning Engineer",
        "start": 2017,
        "end": 2021,
        "current": false
      },
      {
        "company": "Swiggy",
        "title": "Machine Learning Engineer",
        "start": 2015,
        "end": 2017,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 45%.",
      "Re-architected the checkout flow, improving conversion by 40%."
    ],
    "certifications": [
      "AWS Certified Developer"
    ],
    "languages": [
      "English",
      "Kannada"
    ]
  },
  {
    "id": "cand-008",
    "name": "Divya Menon",
    "role": "Engineering Manager",
    "experience": 2.6,
    "skills": [
      "AWS",
      "System Design",
      "Team Leadership",
      "Roadmapping",
      "Agile"
    ],
    "location": "Bangalore",
    "current_company": "Freshworks",
    "source": "LinkedIn",
    "education": {
      "degree": "B.E Information Science",
      "school": "RV College of Engineering",
      "year": 2021
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Freshworks",
        "title": "Engineering Manager",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Meesho",
        "title": "Engineering Manager",
        "start": 2023,
        "end": 2024,
        "current": false
      }
    ],
    "projects": [
      "Built a real-time recommendation engine serving 20M+ daily active users with sub-100ms latency.",
      "Built an ML-based fraud detection system reducing false positives by 35%.",
      "Owned the payments reconciliation pipeline processing 20M+ transactions per day."
    ],
    "certifications": [
      "TensorFlow Developer Certificate",
      "AWS Certified Developer"
    ],
    "languages": [
      "English",
      "Telugu",
      "Kannada"
    ]
  },
  {
    "id": "cand-009",
    "name": "Vikram Bansal",
    "role": "API Engineer",
    "experience": 7.9,
    "skills": [
      "AWS",
      "MongoDB",
      "Node.js",
      "REST APIs",
      "GraphQL"
    ],
    "location": "Hyderabad",
    "current_company": "Meesho",
    "source": "LinkedIn",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIIT Hyderabad",
      "year": 2016
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Meesho",
        "title": "Senior API Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Flipkart",
        "title": "API Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Microsoft",
        "title": "API Engineer",
        "start": 2018,
        "end": 2022,
        "current": false
      }
    ],
    "projects": [
      "Owned the payments reconciliation pipeline processing 5M+ transactions per day.",
      "Built an internal observability platform adopted company-wide, cutting MTTR by 35%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Telugu",
      "Kannada"
    ]
  },
  {
    "id": "cand-010",
    "name": "Meera Kumar",
    "role": "Site Reliability Engineer",
    "experience": 14.0,
    "skills": [
      "AWS",
      "Go",
      "Kubernetes",
      "Terraform",
      "Grafana"
    ],
    "location": "Pune",
    "current_company": "Razorpay",
    "source": "AlphaSource Network",
    "education": {
      "degree": "MCA",
      "school": "Anna University",
      "year": 2009
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Razorpay",
        "title": "Senior Site Reliability Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Amazon",
        "title": "Site Reliability Engineer",
        "start": 2021,
        "end": 2024,
        "current": false
      },
      {
        "company": "Freshworks",
        "title": "Site Reliability Engineer",
        "start": 2018,
        "end": 2021,
        "current": false
      },
      {
        "company": "Accenture",
        "title": "Site Reliability Engineer",
        "start": 2015,
        "end": 2018,
        "current": false
      }
    ],
    "projects": [
      "Led a team of 3 engineers building the company's first multi-region deployment.",
      "Built an ML-based fraud detection system reducing false positives by 30%."
    ],
    "certifications": [
      "TensorFlow Developer Certificate"
    ],
    "languages": [
      "English",
      "Kannada"
    ]
  },
  {
    "id": "cand-011",
    "name": "Rahul Rastogi",
    "role": "Backend Engineer",
    "experience": 11.1,
    "skills": [
      "AWS",
      "Java",
      "PostgreSQL",
      "Kafka",
      "Microservices"
    ],
    "location": "Gurgaon",
    "current_company": "Zoho",
    "source": "LinkedIn",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "NIT Surathkal",
      "year": 2012
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Zoho",
        "title": "Senior Backend Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Microsoft",
        "title": "Backend Engineer",
        "start": 2020,
        "end": 2023,
        "current": false
      },
      {
        "company": "TCS",
        "title": "Backend Engineer",
        "start": 2019,
        "end": 2020,
        "current": false
      },
      {
        "company": "Meesho",
        "title": "Backend Engineer",
        "start": 2016,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Built a real-time recommendation engine serving 20M+ daily active users with sub-100ms latency.",
      "Owned the payments reconciliation pipeline processing 12M+ transactions per day."
    ],
    "certifications": [
      "Google Cloud Professional ML Engineer",
      "PMP"
    ],
    "languages": [
      "English",
      "Marathi"
    ]
  },
  {
    "id": "cand-012",
    "name": "Isha Shetty",
    "role": "Product Engineer",
    "experience": 4.8,
    "skills": [
      "Node.js",
      "GraphQL",
      "TypeScript",
      "React",
      "Kubernetes"
    ],
    "location": "Chennai",
    "current_company": "Adobe",
    "source": "LinkedIn",
    "education": {
      "degree": "M.S Computer Science",
      "school": "IIT Kanpur",
      "year": 2019
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Adobe",
        "title": "Product Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Freshworks",
        "title": "Product Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      }
    ],
    "projects": [
      "Built an internal observability platform adopted company-wide, cutting MTTR by 18%.",
      "Led migration of 12 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 40%.",
      "Built a real-time recommendation engine serving 3M+ daily active users with sub-100ms latency."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Kannada",
      "Tamil"
    ]
  },
  {
    "id": "cand-013",
    "name": "Nikhil Rao",
    "role": "Data Scientist",
    "experience": 12.1,
    "skills": [
      "Machine Learning",
      "TensorFlow",
      "Statistics",
      "NLP",
      "SQL"
    ],
    "location": "Mumbai",
    "current_company": "Salesforce",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Bombay",
      "year": 2011
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Salesforce",
        "title": "Senior Data Scientist",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Accenture",
        "title": "Data Scientist",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "Google",
        "title": "Data Scientist",
        "start": 2018,
        "end": 2021,
        "current": false
      },
      {
        "company": "Zoho",
        "title": "Data Scientist",
        "start": 2015,
        "end": 2018,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 18%.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 30%."
    ],
    "certifications": [
      "Google Cloud Professional ML Engineer",
      "Certified Scrum Master"
    ],
    "languages": [
      "English",
      "Kannada",
      "Tamil"
    ]
  },
  {
    "id": "cand-014",
    "name": "Pooja Malhotra",
    "role": "DevOps Engineer",
    "experience": 3.0,
    "skills": [
      "Kubernetes",
      "AWS",
      "Ansible",
      "CI/CD",
      "Terraform"
    ],
    "location": "Noida",
    "current_company": "Oracle",
    "source": "Referral",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Delhi",
      "year": 2020
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Oracle",
        "title": "DevOps Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      }
    ],
    "projects": [
      "Designed and shipped an internal search platform reducing on-call incident triage time by 35%.",
      "Led a team of 20 engineers building the company's first multi-region deployment.",
      "Built a real-time recommendation engine serving 3M+ daily active users with sub-100ms latency."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Tamil"
    ]
  },
  {
    "id": "cand-015",
    "name": "Aman Desai",
    "role": "Frontend Engineer",
    "experience": 12.8,
    "skills": [
      "Tailwind CSS",
      "TypeScript",
      "React",
      "Redux",
      "Next.js"
    ],
    "location": "Bangalore",
    "current_company": "IBM",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Information Technology",
      "school": "NIT Trichy",
      "year": 2011
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "IBM",
        "title": "Senior Frontend Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Adobe",
        "title": "Frontend Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Atlassian",
        "title": "Frontend Engineer",
        "start": 2019,
        "end": 2022,
        "current": false
      },
      {
        "company": "Zoho",
        "title": "Frontend Engineer",
        "start": 2016,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Designed and shipped an internal search platform reducing on-call incident triage time by 22%.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 18%.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 30%."
    ],
    "certifications": [
      "Google Cloud Professional ML Engineer"
    ],
    "languages": [
      "English",
      "Kannada",
      "Hindi"
    ]
  },
  {
    "id": "cand-016",
    "name": "Riya Saxena",
    "role": "Platform Engineer",
    "experience": 11.9,
    "skills": [
      "Site Reliability",
      "Kubernetes",
      "IAM",
      "AWS",
      "Go"
    ],
    "location": "Hyderabad",
    "current_company": "Infosys",
    "source": "Referral",
    "education": {
      "degree": "B.E Computer Science",
      "school": "BITS Pilani",
      "year": 2012
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "Infosys",
        "title": "Senior Platform Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Adobe",
        "title": "Platform Engineer",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "Razorpay",
        "title": "Platform Engineer",
        "start": 2019,
        "end": 2021,
        "current": false
      },
      {
        "company": "Oracle",
        "title": "Platform Engineer",
        "start": 2018,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 30%.",
      "Re-architected the checkout flow, improving conversion by 40%.",
      "Led a team of 50 engineers building the company's first multi-region deployment."
    ],
    "certifications": [
      "AWS Certified Solutions Architect"
    ],
    "languages": [
      "English",
      "Tamil"
    ]
  },
  {
    "id": "cand-017",
    "name": "Siddharth Sinha",
    "role": "Machine Learning Engineer",
    "experience": 7.5,
    "skills": [
      "Docker",
      "MLOps",
      "Python",
      "Computer Vision",
      "NLP"
    ],
    "location": "Pune",
    "current_company": "TCS",
    "source": "AlphaSource Network",
    "education": {
      "degree": "B.Tech Electronics",
      "school": "IIT Madras",
      "year": 2016
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "TCS",
        "title": "Senior Machine Learning Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Oracle",
        "title": "Machine Learning Engineer",
        "start": 2021,
        "end": 2024,
        "current": false
      },
      {
        "company": "Flipkart",
        "title": "Machine Learning Engineer",
        "start": 2019,
        "end": 2021,
        "current": false
      }
    ],
    "projects": [
      "Led migration of 20 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 40%.",
      "Owned the payments reconciliation pipeline processing 8M+ transactions per day.",
      "Built a real-time recommendation engine serving 50M+ daily active users with sub-100ms latency."
    ],
    "certifications": [
      "Certified Scrum Master",
      "TensorFlow Developer Certificate"
    ],
    "languages": [
      "English",
      "Bengali"
    ]
  },
  {
    "id": "cand-018",
    "name": "Neha Sethi",
    "role": "Engineering Manager",
    "experience": 10.5,
    "skills": [
      "Agile",
      "AWS",
      "Java",
      "Team Leadership",
      "Roadmapping"
    ],
    "location": "Gurgaon",
    "current_company": "Accenture",
    "source": "Career Site",
    "education": {
      "degree": "M.Tech Computer Science",
      "school": "IISc Bangalore",
      "year": 2013
    },
    "notice_period": "90 days",
    "timeline": [
      {
        "company": "Accenture",
        "title": "Senior Engineering Manager",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Swiggy",
        "title": "Engineering Manager",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "Atlassian",
        "title": "Engineering Manager",
        "start": 2018,
        "end": 2021,
        "current": false
      },
      {
        "company": "Infosys",
        "title": "Engineering Manager",
        "start": 2016,
        "end": 2018,
        "current": false
      }
    ],
    "projects": [
      "Led a team of 20 engineers building the company's first multi-region deployment.",
      "Built an ML-based fraud detection system reducing false positives by 22%.",
      "Led a team of 20 engineers building the company's first multi-region deployment."
    ],
    "certifications": [
      "Certified Scrum Master",
      "Google Cloud Professional ML Engineer"
    ],
    "languages": [
      "English",
      "Telugu",
      "Kannada"
    ]
  },
  {
    "id": "cand-019",
    "name": "Varun Mehta",
    "role": "API Engineer",
    "experience": 3.6,
    "skills": [
      "Microservices",
      "REST APIs",
      "AWS",
      "GraphQL",
      "Node.js"
    ],
    "location": "Chennai",
    "current_company": "Google",
    "source": "Referral",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "VIT Vellore",
      "year": 2020
    },
    "notice_period": "15 days",
    "timeline": [
      {
        "company": "Google",
        "title": "API Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Zoho",
        "title": "API Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      }
    ],
    "projects": [
      "Led migration of 5 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 35%.",
      "Built a real-time recommendation engine serving 12M+ daily active users with sub-100ms latency."
    ],
    "certifications": [
      "Google Cloud Professional ML Engineer",
      "Certified Scrum Master"
    ],
    "languages": [
      "English",
      "Telugu",
      "Bengali"
    ]
  },
  {
    "id": "cand-020",
    "name": "Tanya Bose",
    "role": "Site Reliability Engineer",
    "experience": 5.0,
    "skills": [
      "Prometheus",
      "Terraform",
      "Kubernetes",
      "Go",
      "Incident Response"
    ],
    "location": "Mumbai",
    "current_company": "Microsoft",
    "source": "Career Site",
    "education": {
      "degree": "B.E Information Science",
      "school": "RV College of Engineering",
      "year": 2018
    },
    "notice_period": "90 days",
    "timeline": [
      {
        "company": "Microsoft",
        "title": "Site Reliability Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Infosys",
        "title": "Site Reliability Engineer",
        "start": 2021,
        "end": 2023,
        "current": false
      }
    ],
    "projects": [
      "Built an internal observability platform adopted company-wide, cutting MTTR by 35%.",
      "Re-architected the checkout flow, improving conversion by 40%."
    ],
    "certifications": [
      "Azure Solutions Architect Expert",
      "TensorFlow Developer Certificate"
    ],
    "languages": [
      "English",
      "Kannada",
      "Telugu"
    ]
  },
  {
    "id": "cand-021",
    "name": "Aarav Bhatt",
    "role": "Backend Engineer",
    "experience": 9.7,
    "skills": [
      "PostgreSQL",
      "Microservices",
      "Spring Boot",
      "Kubernetes",
      "AWS"
    ],
    "location": "Noida",
    "current_company": "Amazon",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIIT Hyderabad",
      "year": 2014
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Amazon",
        "title": "Senior Backend Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Infosys",
        "title": "Backend Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Flipkart",
        "title": "Backend Engineer",
        "start": 2020,
        "end": 2022,
        "current": false
      },
      {
        "company": "Salesforce",
        "title": "Backend Engineer",
        "start": 2017,
        "end": 2020,
        "current": false
      }
    ],
    "projects": [
      "Designed and shipped an internal search platform reducing on-call incident triage time by 35%.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 22%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Telugu",
      "Tamil"
    ]
  },
  {
    "id": "cand-022",
    "name": "Kavya Pandey",
    "role": "Product Engineer",
    "experience": 12.9,
    "skills": [
      "Node.js",
      "AWS",
      "Kubernetes",
      "System Design",
      "TypeScript"
    ],
    "location": "Bangalore",
    "current_company": "Flipkart",
    "source": "Referral",
    "education": {
      "degree": "MCA",
      "school": "Anna University",
      "year": 2011
    },
    "notice_period": "90 days",
    "timeline": [
      {
        "company": "Flipkart",
        "title": "Senior Product Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Google",
        "title": "Product Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Oracle",
        "title": "Product Engineer",
        "start": 2019,
        "end": 2022,
        "current": false
      },
      {
        "company": "Meesho",
        "title": "Product Engineer",
        "start": 2016,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Owned the payments reconciliation pipeline processing 12M+ transactions per day.",
      "Built an ML-based fraud detection system reducing false positives by 35%.",
      "Led migration of 12 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 30%."
    ],
    "certifications": [
      "Azure Solutions Architect Expert",
      "Certified Scrum Master"
    ],
    "languages": [
      "English",
      "Telugu"
    ]
  },
  {
    "id": "cand-023",
    "name": "Rajat Dutta",
    "role": "Data Scientist",
    "experience": 9.0,
    "skills": [
      "Pandas",
      "NLP",
      "Python",
      "SQL",
      "TensorFlow"
    ],
    "location": "Hyderabad",
    "current_company": "Swiggy",
    "source": "LinkedIn",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "NIT Surathkal",
      "year": 2014
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Swiggy",
        "title": "Senior Data Scientist",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Amazon",
        "title": "Data Scientist",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "IBM",
        "title": "Data Scientist",
        "start": 2019,
        "end": 2021,
        "current": false
      },
      {
        "company": "Accenture",
        "title": "Data Scientist",
        "start": 2017,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Re-architected the checkout flow, improving conversion by 35%.",
      "Built an ML-based fraud detection system reducing false positives by 30%.",
      "Built a real-time recommendation engine serving 12M+ daily active users with sub-100ms latency."
    ],
    "certifications": [
      "AWS Certified Solutions Architect",
      "CKA (Certified Kubernetes Administrator"
    ],
    "languages": [
      "English",
      "Bengali"
    ]
  },
  {
    "id": "cand-024",
    "name": "Shreya Verma",
    "role": "DevOps Engineer",
    "experience": 4.8,
    "skills": [
      "Prometheus",
      "Ansible",
      "AWS",
      "Docker",
      "CI/CD"
    ],
    "location": "Pune",
    "current_company": "PhonePe",
    "source": "LinkedIn",
    "education": {
      "degree": "M.S Computer Science",
      "school": "IIT Kanpur",
      "year": 2019
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "PhonePe",
        "title": "DevOps Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Swiggy",
        "title": "DevOps Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      }
    ],
    "projects": [
      "Owned the payments reconciliation pipeline processing 12M+ transactions per day.",
      "Built an ML-based fraud detection system reducing false positives by 22%."
    ],
    "certifications": [
      "AWS Certified Developer",
      "Azure Solutions Architect Expert"
    ],
    "languages": [
      "English",
      "Tamil"
    ]
  },
  {
    "id": "cand-025",
    "name": "Kabir Reddy",
    "role": "Frontend Engineer",
    "experience": 7.1,
    "skills": [
      "Redux",
      "React",
      "Next.js",
      "Tailwind CSS",
      "TypeScript"
    ],
    "location": "Gurgaon",
    "current_company": "Atlassian",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Bombay",
      "year": 2016
    },
    "notice_period": "15 days",
    "timeline": [
      {
        "company": "Atlassian",
        "title": "Senior Frontend Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Amazon",
        "title": "Frontend Engineer",
        "start": 2021,
        "end": 2024,
        "current": false
      },
      {
        "company": "Meesho",
        "title": "Frontend Engineer",
        "start": 2019,
        "end": 2021,
        "current": false
      }
    ],
    "projects": [
      "Led migration of 8 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 40%.",
      "Led a team of 50 engineers building the company's first multi-region deployment."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Hindi",
      "Telugu"
    ]
  },
  {
    "id": "cand-026",
    "name": "Anjali Kulkarni",
    "role": "Platform Engineer",
    "experience": 4.3,
    "skills": [
      "Kubernetes",
      "IAM",
      "EKS",
      "Go",
      "Terraform"
    ],
    "location": "Chennai",
    "current_company": "Freshworks",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Delhi",
      "year": 2019
    },
    "notice_period": "15 days",
    "timeline": [
      {
        "company": "Freshworks",
        "title": "Platform Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Accenture",
        "title": "Platform Engineer",
        "start": 2022,
        "end": 2023,
        "current": false
      }
    ],
    "projects": [
      "Built an internal observability platform adopted company-wide, cutting MTTR by 45%.",
      "Built an ML-based fraud detection system reducing false positives by 22%.",
      "Built a real-time recommendation engine serving 8M+ daily active users with sub-100ms latency."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Marathi",
      "Bengali"
    ]
  },
  {
    "id": "cand-027",
    "name": "Yash Singh",
    "role": "Machine Learning Engineer",
    "experience": 8.1,
    "skills": [
      "MLOps",
      "Python",
      "AWS SageMaker",
      "Computer Vision",
      "NLP"
    ],
    "location": "Mumbai",
    "current_company": "Meesho",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Information Technology",
      "school": "NIT Trichy",
      "year": 2015
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Meesho",
        "title": "Senior Machine Learning Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Razorpay",
        "title": "Machine Learning Engineer",
        "start": 2021,
        "end": 2024,
        "current": false
      },
      {
        "company": "Adobe",
        "title": "Machine Learning Engineer",
        "start": 2018,
        "end": 2021,
        "current": false
      }
    ],
    "projects": [
      "Owned the payments reconciliation pipeline processing 3M+ transactions per day.",
      "Led a team of 12 engineers building the company's first multi-region deployment."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Bengali",
      "Telugu"
    ]
  },
  {
    "id": "cand-028",
    "name": "Simran Naidu",
    "role": "Engineering Manager",
    "experience": 10.5,
    "skills": [
      "System Design",
      "Roadmapping",
      "AWS",
      "Agile",
      "Team Leadership"
    ],
    "location": "Noida",
    "current_company": "Razorpay",
    "source": "Career Site",
    "education": {
      "degree": "B.E Computer Science",
      "school": "BITS Pilani",
      "year": 2013
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Razorpay",
        "title": "Senior Engineering Manager",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Salesforce",
        "title": "Engineering Manager",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "TCS",
        "title": "Engineering Manager",
        "start": 2018,
        "end": 2021,
        "current": false
      },
      {
        "company": "Meesho",
        "title": "Engineering Manager",
        "start": 2016,
        "end": 2018,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 30%.",
      "Owned the payments reconciliation pipeline processing 3M+ transactions per day.",
      "Owned the payments reconciliation pipeline processing 8M+ transactions per day."
    ],
    "certifications": [
      "CKA (Certified Kubernetes Administrator",
      "AWS Certified Developer"
    ],
    "languages": [
      "English",
      "Bengali"
    ]
  },
  {
    "id": "cand-029",
    "name": "Dev Warrier",
    "role": "API Engineer",
    "experience": 5.9,
    "skills": [
      "Node.js",
      "GraphQL",
      "Microservices",
      "AWS",
      "MongoDB"
    ],
    "location": "Bangalore",
    "current_company": "Zoho",
    "source": "Referral",
    "education": {
      "degree": "B.Tech Electronics",
      "school": "IIT Madras",
      "year": 2018
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Zoho",
        "title": "API Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "PhonePe",
        "title": "API Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Razorpay",
        "title": "API Engineer",
        "start": 2020,
        "end": 2022,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 22%.",
      "Built an internal observability platform adopted company-wide, cutting MTTR by 18%."
    ],
    "certifications": [
      "PMP",
      "Google Cloud Professional ML Engineer"
    ],
    "languages": [
      "English",
      "Telugu",
      "Tamil"
    ]
  },
  {
    "id": "cand-030",
    "name": "Radhika Nair",
    "role": "Site Reliability Engineer",
    "experience": 7.1,
    "skills": [
      "Kubernetes",
      "Grafana",
      "AWS",
      "Incident Response",
      "Go"
    ],
    "location": "Hyderabad",
    "current_company": "Adobe",
    "source": "AlphaSource Network",
    "education": {
      "degree": "M.Tech Computer Science",
      "school": "IISc Bangalore",
      "year": 2016
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Adobe",
        "title": "Senior Site Reliability Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Microsoft",
        "title": "Site Reliability Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Swiggy",
        "title": "Site Reliability Engineer",
        "start": 2020,
        "end": 2022,
        "current": false
      }
    ],
    "projects": [
      "Built a real-time recommendation engine serving 20M+ daily active users with sub-100ms latency.",
      "Owned the payments reconciliation pipeline processing 20M+ transactions per day."
    ],
    "certifications": [
      "TensorFlow Developer Certificate"
    ],
    "languages": [
      "English",
      "Marathi",
      "Telugu"
    ]
  },
  {
    "id": "cand-031",
    "name": "Manish Joshi",
    "role": "Backend Engineer",
    "experience": 9.7,
    "skills": [
      "Java",
      "PostgreSQL",
      "Kafka",
      "Docker",
      "Spring Boot"
    ],
    "location": "Pune",
    "current_company": "Salesforce",
    "source": "Referral",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "VIT Vellore",
      "year": 2014
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Salesforce",
        "title": "Senior Backend Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Amazon",
        "title": "Backend Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "PhonePe",
        "title": "Backend Engineer",
        "start": 2021,
        "end": 2022,
        "current": false
      },
      {
        "company": "Flipkart",
        "title": "Backend Engineer",
        "start": 2019,
        "end": 2021,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 22%.",
      "Built an ML-based fraud detection system reducing false positives by 30%.",
      "Built an internal observability platform adopted company-wide, cutting MTTR by 45%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Bengali",
      "Marathi"
    ]
  },
  {
    "id": "cand-032",
    "name": "Swati Chawla",
    "role": "Product Engineer",
    "experience": 4.2,
    "skills": [
      "Node.js",
      "AWS",
      "TypeScript",
      "Kubernetes",
      "React"
    ],
    "location": "Gurgaon",
    "current_company": "Oracle",
    "source": "LinkedIn",
    "education": {
      "degree": "B.E Information Science",
      "school": "RV College of Engineering",
      "year": 2019
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Oracle",
        "title": "Product Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Swiggy",
        "title": "Product Engineer",
        "start": 2023,
        "end": 2024,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 18%.",
      "Built an internal observability platform adopted company-wide, cutting MTTR by 30%.",
      "Led a team of 8 engineers building the company's first multi-region deployment."
    ],
    "certifications": [
      "TensorFlow Developer Certificate",
      "Google Cloud Professional ML Engineer"
    ],
    "languages": [
      "English",
      "Marathi"
    ]
  },
  {
    "id": "cand-033",
    "name": "Harsh Chandra",
    "role": "Data Scientist",
    "experience": 3.6,
    "skills": [
      "SQL",
      "Statistics",
      "TensorFlow",
      "Pandas",
      "Python"
    ],
    "location": "Chennai",
    "current_company": "IBM",
    "source": "AlphaSource Network",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIIT Hyderabad",
      "year": 2020
    },
    "notice_period": "90 days",
    "timeline": [
      {
        "company": "IBM",
        "title": "Data Scientist",
        "start": 2022,
        "end": 2026,
        "current": true
      }
    ],
    "projects": [
      "Led migration of 5 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 35%.",
      "Built an internal observability platform adopted company-wide, cutting MTTR by 22%.",
      "Led a team of 50 engineers building the company's first multi-region deployment."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Tamil",
      "Telugu"
    ]
  },
  {
    "id": "cand-034",
    "name": "Nidhi Bhatia",
    "role": "DevOps Engineer",
    "experience": 7.2,
    "skills": [
      "Kubernetes",
      "Ansible",
      "AWS",
      "Terraform",
      "CI/CD"
    ],
    "location": "Mumbai",
    "current_company": "Infosys",
    "source": "Career Site",
    "education": {
      "degree": "MCA",
      "school": "Anna University",
      "year": 2016
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "Infosys",
        "title": "Senior DevOps Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Razorpay",
        "title": "DevOps Engineer",
        "start": 2020,
        "end": 2023,
        "current": false
      },
      {
        "company": "Salesforce",
        "title": "DevOps Engineer",
        "start": 2019,
        "end": 2020,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 18%.",
      "Led a team of 20 engineers building the company's first multi-region deployment.",
      "Built an internal observability platform adopted company-wide, cutting MTTR by 18%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Marathi",
      "Telugu"
    ]
  },
  {
    "id": "cand-035",
    "name": "Akash Prabhu",
    "role": "Frontend Engineer",
    "experience": 13.2,
    "skills": [
      "React",
      "TypeScript",
      "Next.js",
      "Tailwind CSS",
      "Webpack"
    ],
    "location": "Noida",
    "current_company": "TCS",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "NIT Surathkal",
      "year": 2010
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "TCS",
        "title": "Senior Frontend Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Infosys",
        "title": "Frontend Engineer",
        "start": 2020,
        "end": 2023,
        "current": false
      },
      {
        "company": "Flipkart",
        "title": "Frontend Engineer",
        "start": 2018,
        "end": 2020,
        "current": false
      },
      {
        "company": "Google",
        "title": "Frontend Engineer",
        "start": 2016,
        "end": 2018,
        "current": false
      }
    ],
    "projects": [
      "Led a team of 3 engineers building the company's first multi-region deployment.",
      "Built a real-time recommendation engine serving 12M+ daily active users with sub-100ms latency."
    ],
    "certifications": [
      "CKA (Certified Kubernetes Administrator",
      "Google Cloud Professional ML Engineer"
    ],
    "languages": [
      "English",
      "Marathi",
      "Tamil"
    ]
  },
  {
    "id": "cand-036",
    "name": "Deepika Gupta",
    "role": "Platform Engineer",
    "experience": 8.8,
    "skills": [
      "Site Reliability",
      "IAM",
      "Go",
      "AWS",
      "Terraform"
    ],
    "location": "Bangalore",
    "current_company": "Accenture",
    "source": "Career Site",
    "education": {
      "degree": "M.S Computer Science",
      "school": "IIT Kanpur",
      "year": 2015
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "Accenture",
        "title": "Senior Platform Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Atlassian",
        "title": "Platform Engineer",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "Swiggy",
        "title": "Platform Engineer",
        "start": 2018,
        "end": 2021,
        "current": false
      }
    ],
    "projects": [
      "Re-architected the checkout flow, improving conversion by 30%.",
      "Led migration of 8 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 45%.",
      "Built an ML-based fraud detection system reducing false positives by 40%."
    ],
    "certifications": [
      "TensorFlow Developer Certificate",
      "Azure Solutions Architect Expert"
    ],
    "languages": [
      "English",
      "Telugu"
    ]
  },
  {
    "id": "cand-037",
    "name": "Sahil Chatterjee",
    "role": "Machine Learning Engineer",
    "experience": 13.2,
    "skills": [
      "MLOps",
      "Computer Vision",
      "Docker",
      "AWS SageMaker",
      "PyTorch"
    ],
    "location": "Hyderabad",
    "current_company": "Google",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Bombay",
      "year": 2010
    },
    "notice_period": "15 days",
    "timeline": [
      {
        "company": "Google",
        "title": "Senior Machine Learning Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Meesho",
        "title": "Machine Learning Engineer",
        "start": 2020,
        "end": 2023,
        "current": false
      },
      {
        "company": "Oracle",
        "title": "Machine Learning Engineer",
        "start": 2018,
        "end": 2020,
        "current": false
      },
      {
        "company": "Swiggy",
        "title": "Machine Learning Engineer",
        "start": 2016,
        "end": 2018,
        "current": false
      }
    ],
    "projects": [
      "Led a team of 50 engineers building the company's first multi-region deployment.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 18%.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 40%."
    ],
    "certifications": [
      "AWS Certified Developer"
    ],
    "languages": [
      "English",
      "Hindi",
      "Marathi"
    ]
  },
  {
    "id": "cand-038",
    "name": "Ritu Agarwal",
    "role": "Engineering Manager",
    "experience": 3.4,
    "skills": [
      "System Design",
      "Team Leadership",
      "Java",
      "AWS",
      "Roadmapping"
    ],
    "location": "Pune",
    "current_company": "Microsoft",
    "source": "LinkedIn",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Delhi",
      "year": 2020
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Microsoft",
        "title": "Engineering Manager",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Adobe",
        "title": "Engineering Manager",
        "start": 2023,
        "end": 2023,
        "current": false
      }
    ],
    "projects": [
      "Re-architected the checkout flow, improving conversion by 40%.",
      "Led a team of 8 engineers building the company's first multi-region deployment."
    ],
    "certifications": [
      "TensorFlow Developer Certificate",
      "Azure Solutions Architect Expert"
    ],
    "languages": [
      "English",
      "Marathi"
    ]
  },
  {
    "id": "cand-039",
    "name": "Tarun Mishra",
    "role": "API Engineer",
    "experience": 7.5,
    "skills": [
      "REST APIs",
      "Node.js",
      "Microservices",
      "GraphQL",
      "AWS"
    ],
    "location": "Gurgaon",
    "current_company": "Amazon",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Information Technology",
      "school": "NIT Trichy",
      "year": 2016
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Amazon",
        "title": "Senior API Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Swiggy",
        "title": "API Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Infosys",
        "title": "API Engineer",
        "start": 2021,
        "end": 2022,
        "current": false
      }
    ],
    "projects": [
      "Led migration of 8 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 30%.",
      "Re-architected the checkout flow, improving conversion by 22%.",
      "Owned the payments reconciliation pipeline processing 20M+ transactions per day."
    ],
    "certifications": [
      "CKA (Certified Kubernetes Administrator",
      "AWS Certified Developer"
    ],
    "languages": [
      "English",
      "Hindi"
    ]
  },
  {
    "id": "cand-040",
    "name": "Preeti Ghosh",
    "role": "Site Reliability Engineer",
    "experience": 4.1,
    "skills": [
      "Go",
      "Terraform",
      "Prometheus",
      "AWS",
      "Grafana"
    ],
    "location": "Chennai",
    "current_company": "Flipkart",
    "source": "Referral",
    "education": {
      "degree": "B.E Computer Science",
      "school": "BITS Pilani",
      "year": 2019
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "Flipkart",
        "title": "Site Reliability Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Razorpay",
        "title": "Site Reliability Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      }
    ],
    "projects": [
      "Built an ML-based fraud detection system reducing false positives by 40%.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 35%.",
      "Re-architected the checkout flow, improving conversion by 30%."
    ],
    "certifications": [
      "Azure Solutions Architect Expert",
      "Certified Scrum Master"
    ],
    "languages": [
      "English",
      "Telugu",
      "Tamil"
    ]
  },
  {
    "id": "cand-041",
    "name": "Vivek Sharma",
    "role": "Backend Engineer",
    "experience": 6.9,
    "skills": [
      "Microservices",
      "Docker",
      "AWS",
      "Java",
      "Spring Boot"
    ],
    "location": "Mumbai",
    "current_company": "Swiggy",
    "source": "AlphaSource Network",
    "education": {
      "degree": "B.Tech Electronics",
      "school": "IIT Madras",
      "year": 2017
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Swiggy",
        "title": "Senior Backend Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Zoho",
        "title": "Backend Engineer",
        "start": 2021,
        "end": 2024,
        "current": false
      },
      {
        "company": "Accenture",
        "title": "Backend Engineer",
        "start": 2019,
        "end": 2021,
        "current": false
      }
    ],
    "projects": [
      "Led migration of 20 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 45%.",
      "Built an internal observability platform adopted company-wide, cutting MTTR by 22%."
    ],
    "certifications": [
      "Certified Scrum Master",
      "AWS Certified Developer"
    ],
    "languages": [
      "English",
      "Marathi"
    ]
  },
  {
    "id": "cand-042",
    "name": "Sanya Kapoor",
    "role": "Product Engineer",
    "experience": 9.9,
    "skills": [
      "GraphQL",
      "System Design",
      "Kubernetes",
      "AWS",
      "React"
    ],
    "location": "Noida",
    "current_company": "PhonePe",
    "source": "LinkedIn",
    "education": {
      "degree": "M.Tech Computer Science",
      "school": "IISc Bangalore",
      "year": 2014
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "PhonePe",
        "title": "Senior Product Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Infosys",
        "title": "Product Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "Microsoft",
        "title": "Product Engineer",
        "start": 2019,
        "end": 2022,
        "current": false
      },
      {
        "company": "Zoho",
        "title": "Product Engineer",
        "start": 2016,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Designed and shipped an internal search platform reducing on-call incident triage time by 22%.",
      "Re-architected the checkout flow, improving conversion by 40%.",
      "Built an ML-based fraud detection system reducing false positives by 30%."
    ],
    "certifications": [
      "PMP"
    ],
    "languages": [
      "English",
      "Hindi",
      "Telugu"
    ]
  },
  {
    "id": "cand-043",
    "name": "Abhishek Pillai",
    "role": "Data Scientist",
    "experience": 11.6,
    "skills": [
      "Machine Learning",
      "NLP",
      "SQL",
      "TensorFlow",
      "Python"
    ],
    "location": "Bangalore",
    "current_company": "Atlassian",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "VIT Vellore",
      "year": 2012
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Atlassian",
        "title": "Senior Data Scientist",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Razorpay",
        "title": "Data Scientist",
        "start": 2021,
        "end": 2024,
        "current": false
      },
      {
        "company": "Flipkart",
        "title": "Data Scientist",
        "start": 2019,
        "end": 2021,
        "current": false
      },
      {
        "company": "Meesho",
        "title": "Data Scientist",
        "start": 2016,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Built a real-time recommendation engine serving 50M+ daily active users with sub-100ms latency.",
      "Built an internal observability platform adopted company-wide, cutting MTTR by 40%.",
      "Re-architected the checkout flow, improving conversion by 22%."
    ],
    "certifications": [
      "AWS Certified Developer",
      "Certified Scrum Master"
    ],
    "languages": [
      "English",
      "Bengali",
      "Tamil"
    ]
  },
  {
    "id": "cand-044",
    "name": "Komal Kaur",
    "role": "DevOps Engineer",
    "experience": 14.0,
    "skills": [
      "AWS",
      "Terraform",
      "Prometheus",
      "Docker",
      "Ansible"
    ],
    "location": "Hyderabad",
    "current_company": "Freshworks",
    "source": "AlphaSource Network",
    "education": {
      "degree": "B.E Information Science",
      "school": "RV College of Engineering",
      "year": 2009
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Freshworks",
        "title": "Senior DevOps Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Flipkart",
        "title": "DevOps Engineer",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "Meesho",
        "title": "DevOps Engineer",
        "start": 2019,
        "end": 2021,
        "current": false
      },
      {
        "company": "Infosys",
        "title": "DevOps Engineer",
        "start": 2016,
        "end": 2019,
        "current": false
      }
    ],
    "projects": [
      "Designed and shipped an internal search platform reducing on-call incident triage time by 45%.",
      "Built a real-time recommendation engine serving 12M+ daily active users with sub-100ms latency.",
      "Led a team of 8 engineers building the company's first multi-region deployment."
    ],
    "certifications": [
      "Certified Scrum Master",
      "AWS Certified Developer"
    ],
    "languages": [
      "English",
      "Telugu",
      "Kannada"
    ]
  },
  {
    "id": "cand-045",
    "name": "Gaurav Trivedi",
    "role": "Frontend Engineer",
    "experience": 5.7,
    "skills": [
      "React",
      "Next.js",
      "Redux",
      "Webpack",
      "TypeScript"
    ],
    "location": "Pune",
    "current_company": "Meesho",
    "source": "Referral",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIIT Hyderabad",
      "year": 2018
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Meesho",
        "title": "Frontend Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Infosys",
        "title": "Frontend Engineer",
        "start": 2020,
        "end": 2023,
        "current": false
      }
    ],
    "projects": [
      "Led migration of 8 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 22%.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 22%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Marathi"
    ]
  },
  {
    "id": "cand-046",
    "name": "Ishita Krishnan",
    "role": "Platform Engineer",
    "experience": 2.5,
    "skills": [
      "Site Reliability",
      "AWS",
      "EKS",
      "Go",
      "Terraform"
    ],
    "location": "Gurgaon",
    "current_company": "Razorpay",
    "source": "AlphaSource Network",
    "education": {
      "degree": "MCA",
      "school": "Anna University",
      "year": 2021
    },
    "notice_period": "15 days",
    "timeline": [
      {
        "company": "Razorpay",
        "title": "Platform Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      }
    ],
    "projects": [
      "Built a real-time recommendation engine serving 50M+ daily active users with sub-100ms latency.",
      "Designed and shipped an internal search platform reducing on-call incident triage time by 30%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Hindi",
      "Kannada"
    ]
  },
  {
    "id": "cand-047",
    "name": "Suraj Iyer",
    "role": "Machine Learning Engineer",
    "experience": 3.2,
    "skills": [
      "Python",
      "PyTorch",
      "AWS SageMaker",
      "Computer Vision",
      "MLOps"
    ],
    "location": "Chennai",
    "current_company": "Zoho",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "NIT Surathkal",
      "year": 2020
    },
    "notice_period": "60 days",
    "timeline": [
      {
        "company": "Zoho",
        "title": "Machine Learning Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Salesforce",
        "title": "Machine Learning Engineer",
        "start": 2023,
        "end": 2024,
        "current": false
      }
    ],
    "projects": [
      "Led migration of 50 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 45%.",
      "Built an ML-based fraud detection system reducing false positives by 45%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Telugu"
    ]
  },
  {
    "id": "cand-048",
    "name": "Payal Menon",
    "role": "Engineering Manager",
    "experience": 3.3,
    "skills": [
      "Java",
      "System Design",
      "Roadmapping",
      "AWS",
      "Team Leadership"
    ],
    "location": "Mumbai",
    "current_company": "Adobe",
    "source": "Career Site",
    "education": {
      "degree": "M.S Computer Science",
      "school": "IIT Kanpur",
      "year": 2020
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Adobe",
        "title": "Engineering Manager",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Zoho",
        "title": "Engineering Manager",
        "start": 2023,
        "end": 2023,
        "current": false
      }
    ],
    "projects": [
      "Re-architected the checkout flow, improving conversion by 40%.",
      "Built an ML-based fraud detection system reducing false positives by 40%.",
      "Led a team of 3 engineers building the company's first multi-region deployment."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Telugu"
    ]
  },
  {
    "id": "cand-049",
    "name": "Rohit Bansal",
    "role": "API Engineer",
    "experience": 7.3,
    "skills": [
      "REST APIs",
      "MongoDB",
      "Node.js",
      "Microservices",
      "GraphQL"
    ],
    "location": "Noida",
    "current_company": "Salesforce",
    "source": "Career Site",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Bombay",
      "year": 2016
    },
    "notice_period": "Immediate joiner",
    "timeline": [
      {
        "company": "Salesforce",
        "title": "Senior API Engineer",
        "start": 2024,
        "end": 2026,
        "current": true
      },
      {
        "company": "Zoho",
        "title": "API Engineer",
        "start": 2022,
        "end": 2024,
        "current": false
      },
      {
        "company": "IBM",
        "title": "API Engineer",
        "start": 2019,
        "end": 2022,
        "current": false
      }
    ],
    "projects": [
      "Built a real-time recommendation engine serving 3M+ daily active users with sub-100ms latency.",
      "Built a real-time recommendation engine serving 12M+ daily active users with sub-100ms latency.",
      "Re-architected the checkout flow, improving conversion by 40%."
    ],
    "certifications": [],
    "languages": [
      "English",
      "Bengali",
      "Hindi"
    ]
  },
  {
    "id": "cand-050",
    "name": "Anusha Kumar",
    "role": "Site Reliability Engineer",
    "experience": 9.4,
    "skills": [
      "Grafana",
      "Terraform",
      "AWS",
      "Kubernetes",
      "Prometheus"
    ],
    "location": "Bangalore",
    "current_company": "Oracle",
    "source": "AlphaSource Network",
    "education": {
      "degree": "B.Tech Computer Science",
      "school": "IIT Delhi",
      "year": 2014
    },
    "notice_period": "30 days",
    "timeline": [
      {
        "company": "Oracle",
        "title": "Senior Site Reliability Engineer",
        "start": 2023,
        "end": 2026,
        "current": true
      },
      {
        "company": "Flipkart",
        "title": "Site Reliability Engineer",
        "start": 2021,
        "end": 2023,
        "current": false
      },
      {
        "company": "Atlassian",
        "title": "Site Reliability Engineer",
        "start": 2020,
        "end": 2021,
        "current": false
      },
      {
        "company": "Amazon",
        "title": "Site Reliability Engineer",
        "start": 2017,
        "end": 2020,
        "current": false
      }
    ],
    "projects": [
      "Built a real-time recommendation engine serving 8M+ daily active users with sub-100ms latency.",
      "Owned the payments reconciliation pipeline processing 12M+ transactions per day.",
      "Led migration of 20 monolith services to a Kubernetes-based microservices architecture, reducing deployment time by 45%."
    ],
    "certifications": [
      "PMP",
      "AWS Certified Solutions Architect"
    ],
    "languages": [
      "English",
      "Tamil"
    ]
  }
];
