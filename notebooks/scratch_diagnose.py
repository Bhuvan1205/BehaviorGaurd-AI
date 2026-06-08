import pandas as pd, os, json

CLUSTER_DIR = r'notebooks\models\cluster_models'
df = pd.read_csv(os.path.join(CLUSTER_DIR, 'user_cluster_assignments.csv'))

print('=== FAILURE ANALYSIS ===\n')

# F1/F2: Users not in all 3 shifts
user_shifts = df.groupby('user_id')['shift'].nunique()
print(f'Users in exactly 3 shifts: {(user_shifts==3).sum()}')
print(f'Users in exactly 2 shifts: {(user_shifts==2).sum()}')
print(f'Users in exactly 1 shift : {(user_shifts==1).sum()}')

# Which shifts are missing per user?
all_shifts = {"Day", "Evening", "Night"}
user_shift_sets = df.groupby('user_id')['shift'].apply(set)
missing_shift_counts = user_shift_sets.apply(lambda s: frozenset(all_shifts - s)).value_counts()
print('\nMissing shift combinations (per user):')
print(missing_shift_counts.to_string())

# F3/F4: 8 missing combos
print('\n\nCombos in CSV but NOT in thresholds:')
with open(os.path.join(CLUSTER_DIR, 'cluster_thresholds.json')) as f:
    thresholds = json.load(f)
threshold_keys = set(thresholds.keys())

def make_key(row):
    return f"{row['shift']}_{row['role_group']}_{row['cluster_id']}"

df['combo_key'] = df.apply(make_key, axis=1)
csv_combos = set(df['combo_key'].unique())
missing = csv_combos - threshold_keys
for m in sorted(missing):
    count = (df['combo_key'] == m).sum()
    print(f'  {m}: {count} users affected')

print('\n\nTotal affected users (in missing combos):')
affected = df[df['combo_key'].isin(missing)]
print(f'  {affected["user_id"].nunique()} unique users across {len(affected)} rows')
print('\nSample:')
print(affected.head(10).to_string(index=False))
