import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

# Assuming you have a CSV file with columns: date, number1, number2, etc.
df = pd.read_csv('lotto_data.csv')

# Flatten all number columns into a single list
all_numbers = df.iloc[:, 1:].values.flatten()

# Count frequency of each number
number_frequency = Counter(all_numbers)

# Plot frequency of numbers
plt.figure(figsize=(12, 6))
plt.bar(number_frequency.keys(), number_frequency.values())
plt.title('Frequency of Lottery Numbers')
plt.xlabel('Number')
plt.ylabel('Frequency')
plt.show()

# Find most common numbers
most_common = number_frequency.most_common(10)
print("Most common numbers:", most_common)

# Find least common numbers
least_common = number_frequency.most_common()[:-11:-1]
print("Least common numbers:", least_common)

# Calculate average time between appearances for each number
def avg_time_between(number):
    appearances = df[df.iloc[:, 1:].isin([number]).any(axis=1)].index.tolist()
    if len(appearances) < 2:
        return None
    diffs = [appearances[i+1] - appearances[i] for i in range(len(appearances)-1)]
    return sum(diffs) / len(diffs)

avg_times = {num: avg_time_between(num) for num in set(all_numbers)}
print("Average draws between appearances:", avg_times)