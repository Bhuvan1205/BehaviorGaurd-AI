import pandas as pd
from datetime import datetime

def load_users(path):
    return pd.read_csv(path)


def clean_users(df):
  # fill nulls, normalize text
  cat_cols = ['projects','team','department','supervisor','functional_unit']
  df[cat_cols] = df[cat_cols].fillna('unassigned') 
  #converting start date and end date to date-time datatype
  df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
  df['end_date']   = pd.to_datetime(df['end_date'], errors='coerce')
  today = pd.Timestamp.today()
  df['end_date'] = df['end_date'].fillna(today)
  df['tenure_days'] = (df['end_date'] - df['start_date']).dt.days
  #converting all the features to lower case
  df.employee_name=df.employee_name.str.lower()
  df.email=df.email.str.lower()
  df.role=df.role.str.lower()
  df.projects=df.projects.str.lower()
  df.department=df.department.str.lower()
  df.functional_unit=df.functional_unit.str.lower()
  df.supervisor=df.supervisor.str.lower()
  df.team=df.team.str.lower()
  return df


def create_context_features(df):
  # is_new, is_privileged, etc.
  admin_roles = [
    'itadmin', 'president', 'vicepresident', 'director', 
    'chiefengineer', 'manager', 'accountant', 'attorney', 
    'humanresourcespecialist', 'systemsengineer', 'securityguard', 
    'financialanalyst', 'administrativeassistant', 'projectmanager',
    'labmanager', 'purchasingclerk', 'supervisor']  
    
  # 1. Strip whitespace from strings just in case
  df['role'] = df['role'].str.strip()
  df['supervisor'] = df['supervisor'].str.strip()
  df['projects'] = df['projects'].str.strip()

  # 2. Tenure check (is_new)
  df['is_new'] = (df['tenure_days'] < 100).astype(int)


  # 3. Supervisor and Project checks (using != 'unassigned')
  df['has_supervisor'] = (df['supervisor'] != 'unassigned').astype(int)
  df['has_project'] = (df['projects'] != 'unassigned').astype(int)

  # 4. Privileged check (using .isin)
  df['is_privileged'] = df['role'].isin(admin_roles).astype(int)

  # 5. Rare Role check (count occurrences across the whole column)
  # This maps the value_counts back to the original rows
  role_counts = df['role'].value_counts()
  df['rare_role'] = df['role'].map(role_counts).le(5).astype(int)
  return df


def compute_risk_score(df):
    df['risk_score'] = (
        0.3 * df['is_privileged'] +
        0.2 * df['rare_role'] +
        0.2 * (1 - df['has_supervisor']) +
        0.15 * df['is_new'] +
        0.15 * (1 - df['has_project'])
    )
    return df


def build_user_profile(path, output_path):
    df = load_users(path)
    df = clean_users(df)
    df = create_context_features(df)
    df = compute_risk_score(df)
    df.to_csv(output_path, index=False)



build_user_profile(
  "data/raw/users.csv",
  "data/processed/user_profiles_v0.csv"
)


df=pd.read_csv("data/processed/user_profiles_v0.csv")
print(df.isna().sum())
print(df.risk_score.describe())