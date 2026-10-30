import pandas as pd
import matplotlib.pyplot as plt

# Load the Excel file
df = pd.read_excel('Skeletal_Summary_Data_1779396895.xlsx')

# Extract data using column names (case-sensitive)
x = df['Timestamp']
y = df['Avg']

# Create the plot
plt.plot(x, y, marker='o', linestyle='-', color='b')

# Add labels and title
plt.xlabel('Timestamp')
plt.ylabel('Avg')
plt.title('Tracking Skeletal Muscle Movement')

# Show the plot
plt.show()
