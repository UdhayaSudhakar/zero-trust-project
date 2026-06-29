import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Seed for reproducibility
np.random.seed(42)
random.seed(42)

n_samples = 1000

# Generate session data
data = {
    'user_id': [f'U{random.randint(1,100):03d}' for _ in range(n_samples)],
    'session_id': [f'S{i:04d}' for i in range(n_samples)],
    'login_frequency': np.random.randint(1, 20, n_samples),
    'session_duration': np.random.uniform(1, 120, n_samples).round(2),
    'ip_changes': np.random.randint(0, 5, n_samples),
    'pages_visited': np.random.randint(1, 50, n_samples),
    'failed_attempts': np.random.randint(0, 10, n_samples),
    'new_device': np.random.randint(0, 2, n_samples),
    'odd_hours': np.random.randint(0, 2, n_samples),
    'data_accessed_mb': np.random.uniform(0.1, 500, n_samples).round(2),
}

df = pd.DataFrame(data)

# Generate labels
def label_session(row):
    score = 0
    if row['failed_attempts'] > 5: score += 2
    if row['ip_changes'] > 2: score += 2
    if row['new_device'] == 1: score += 1
    if row['odd_hours'] == 1: score += 1
    if row['data_accessed_mb'] > 400: score += 2
    if row['login_frequency'] > 15: score += 1
    if score >= 5: return 'High'
    elif score >= 3: return 'Medium'
    else: return 'Low'

df['risk_level'] = df.apply(label_session, axis=1)
df['trust_score'] = df['risk_level'].map({'Low': 85, 'Medium': 50, 'High': 20})

# Save
df.to_csv('session_data.csv', index=False)
print("Dataset created! Total records:", len(df))
print(df['risk_level'].value_counts())