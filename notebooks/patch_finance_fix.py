"""
BehaviorGuard-AI -- Finance Group Micro-Patch
==============================================
The V5 notebook maps accountant/financialanalyst -> admin_staff (NOT finance).
4 users ended up with role_group='finance' (from our ROLE_GROUP_MAP) but that
group is too small to cluster and has no IF model.

Fix: re-assign those 4 users' role_group to 'admin_staff' in the CSV
     (matching the actual V5 notebook behaviour), keeping their cluster_id
     pointing to the most-common admin_staff cluster in each shift.
"""
import os, json
import pandas as pd

CLUSTER_DIR    = r'notebooks\models\cluster_models'
ASSIGNMENT_CSV = os.path.join(CLUSTER_DIR, 'user_cluster_assignments.csv')
THRESHOLD_JSON = os.path.join(CLUSTER_DIR, 'cluster_thresholds.json')

df = pd.read_csv(ASSIGNMENT_CSV)
with open(THRESHOLD_JSON) as f:
    thresholds = json.load(f)

print("Finance users in CSV:")
fin = df[df['role_group'] == 'finance']
print(fin.to_string(index=False))
print()

# For each (shift, admin_staff) find the most-common cluster_id (baseline cluster)
admin_mode = (df[df['role_group'] == 'admin_staff']
              .groupby('shift')['cluster_id']
              .agg(lambda x: x.value_counts().idxmax()))
print("admin_staff mode clusters per shift:")
print(admin_mode.to_string())
print()

# Patch: re-assign finance users -> admin_staff
mask = df['role_group'] == 'finance'
for idx, row in df[mask].iterrows():
    new_cid = int(admin_mode.get(row['shift'], 0))
    df.at[idx, 'role_group'] = 'admin_staff'
    df.at[idx, 'cluster_id'] = new_cid
    print(f"  {row['user_id']} | {row['shift']}  finance/{row['cluster_id']} -> admin_staff/{new_cid}")

# Verify no remaining invalid combos
def combo_key(row):
    return f"{row['shift']}_{row['role_group']}_{row['cluster_id']}"

df['_key'] = df.apply(combo_key, axis=1)
invalid = df[~df['_key'].isin(thresholds.keys())]
print(f"\nRemaining invalid combos: {len(invalid)}")
if not invalid.empty:
    print(invalid[['user_id','shift','role_group','cluster_id','_key']].to_string(index=False))

df = df.drop(columns=['_key'])
df.to_csv(ASSIGNMENT_CSV, index=False)
print(f"\nSaved {ASSIGNMENT_CSV}")
print(f"Total rows     : {len(df)}")
print(f"Unique users   : {df['user_id'].nunique()}")
users_not3 = (df.groupby('user_id')['shift'].nunique() != 3).sum()
print(f"Users != 3 shifts: {users_not3}")
print("\nFinance micro-patch complete.")
