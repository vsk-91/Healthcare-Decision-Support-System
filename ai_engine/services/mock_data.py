"""
Mock data for the AI analysis engine.
Each condition has: prediction, confidence, findings, keywords (for symptom matching).
The system picks the best match by keyword overlap with symptoms + medical history.
"""

MOCK_CONDITIONS = [
    {
        "prediction": "Hypertensive Heart Disease",
        "confidence": 0.82,
        "keywords": ["blood pressure", "hypertension", "headache", "chest", "palpitation", "heart", "dizziness", "pressure"],
        "findings": [
            "Elevated blood pressure pattern consistent with hypertension",
            "Left ventricular strain pattern observed in ECG",
            "Symptoms correlate with hypertensive target organ involvement",
            "Family history of cardiovascular disease increases risk profile",
        ],
        "treatment": "ACE inhibitors or ARBs first-line; lifestyle modification; sodium restriction",
    },
    {
        "prediction": "Type 2 Diabetes Mellitus",
        "confidence": 0.79,
        "keywords": ["thirst", "urination", "fatigue", "blurred vision", "weight", "glucose", "sugar", "diabetes", "polyuria", "polydipsia"],
        "findings": [
            "Classic triad of polyuria, polydipsia, and weight loss",
            "Fasting glucose likely above diagnostic threshold",
            "BMI and lifestyle factors consistent with insulin resistance",
            "Symptoms suggest chronic metabolic dysregulation",
        ],
        "treatment": "Metformin first-line; dietary modification; HbA1c monitoring every 3 months",
    },
    {
        "prediction": "Acute Upper Respiratory Infection",
        "confidence": 0.88,
        "keywords": ["cough", "sore throat", "runny nose", "nasal", "cold", "fever", "throat", "congestion", "sneezing", "rhinitis"],
        "findings": [
            "Symptoms consistent with viral upper respiratory tract infection",
            "Fever and cough with nasal congestion - typical viral pattern",
            "No signs of lower respiratory involvement on assessment",
            "Duration and onset pattern suggest self-limiting viral illness",
        ],
        "treatment": "Supportive care; antipyretics; adequate hydration; rest; antibiotics only if bacterial confirmed",
    },
    {
        "prediction": "Iron Deficiency Anemia",
        "confidence": 0.76,
        "keywords": ["fatigue", "weakness", "pale", "anemia", "breathless", "shortness of breath", "iron", "tired", "dizzy", "anaemia"],
        "findings": [
            "Fatigue and pallor consistent with reduced hemoglobin levels",
            "Exertional dyspnea suggests reduced oxygen-carrying capacity",
            "Dietary history suggests inadequate iron intake",
            "Blood workup likely to show microcytic hypochromic anemia",
        ],
        "treatment": "Oral iron supplementation; dietary iron increase; treat underlying cause of blood loss",
    },
    {
        "prediction": "Gastroesophageal Reflux Disease (GERD)",
        "confidence": 0.77,
        "keywords": ["heartburn", "acid", "reflux", "stomach", "nausea", "vomiting", "regurgitation", "chest pain", "indigestion", "epigastric"],
        "findings": [
            "Burning epigastric pain aggravated by lying down - classic GERD",
            "Regurgitation and waterbrash symptoms support diagnosis",
            "Lifestyle factors (spicy food, caffeine, late meals) identified",
            "No alarm symptoms suggesting complicated disease",
        ],
        "treatment": "PPI therapy; dietary modifications; elevate head of bed; avoid triggers",
    },
    {
        "prediction": "Anxiety Disorder",
        "confidence": 0.72,
        "keywords": ["anxiety", "panic", "worry", "nervous", "stress", "palpitation", "restless", "insomnia", "sleep", "tension", "fear"],
        "findings": [
            "Persistent worry and tension with somatic symptoms",
            "Palpitations and sleep disturbance common in anxiety",
            "Symptoms disproportionate to identifiable physical cause",
            "Stressors identified in lifestyle and personal history",
        ],
        "treatment": "CBT first-line; SSRIs if pharmacotherapy needed; stress management techniques",
    },
    {
        "prediction": "Musculoskeletal Back Pain",
        "confidence": 0.85,
        "keywords": ["back", "pain", "lumbar", "spine", "muscle", "posture", "lifting", "sitting", "sciatica", "stiffness"],
        "findings": [
            "Mechanical back pain pattern - worse with movement, better with rest",
            "No neurological deficit on screening - non-radicular pattern",
            "Occupational and postural risk factors present",
            "Muscle spasm and paraspinal tenderness likely on examination",
        ],
        "treatment": "NSAIDs short-term; physiotherapy; core strengthening exercises; postural correction",
    },
    {
        "prediction": "Migraine",
        "confidence": 0.80,
        "keywords": ["headache", "migraine", "nausea", "vomiting", "light", "sound", "aura", "throbbing", "unilateral", "pulsating"],
        "findings": [
            "Unilateral throbbing headache with nausea - migraine pattern",
            "Photophobia and phonophobia support migrainous diagnosis",
            "Trigger factors identified in history",
            "Duration and severity pattern consistent with migraine disorder",
        ],
        "treatment": "Triptans for acute attacks; preventive therapy if >4 attacks/month; trigger avoidance",
    },
]
