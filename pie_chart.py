import matplotlib.pyplot as plt


labels = [15, 30, 45, 10]
sizes = [15, 30, 45, 10]
fig1, ax1 = plt.subplots()
ax1.pie(sizes, labels=labels, autopct="%1.1f%%", shadow=True, startangle=90)
ax1.axis("equal")
plt.show()
