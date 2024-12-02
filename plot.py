import csv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Function to plot the resource usage
def plot_resources():
    # Lists to store time and usage data
    times = []
    cpu_usage = []
    memory_usage = []
    disk_usage = []

    # Read the CSV file and load data
    with open('resource_usage.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row
        
        for row in reader:
            times.append(row[0])
            cpu_usage.append(float(row[1]))
            memory_usage.append(float(row[2]))
            disk_usage.append(float(row[3]))

    # Convert time to datetime objects (only time, no date)
    times = [datetime.strptime(time, '%H:%M:%S') for time in times]

    # Create a figure with subplots for CPU, memory, and disk usage
    plt.figure(figsize=(10, 6))

    # Plot CPU usage
    plt.subplot(3, 1, 1)
    plt.plot(times, cpu_usage, label='CPU Usage (%)', color='r')
    plt.title('CPU Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('CPU Usage (%)')
    plt.xticks(rotation=45)
    plt.grid(True)

    # Set time axis to show every 30 seconds or a minute (adjust as needed)
    plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(interval=1))  # Every 1 minute
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # Plot memory usage
    plt.subplot(3, 1, 2)
    plt.plot(times, memory_usage, label='Memory Usage (%)', color='g')
    plt.title('Memory Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (%)')
    plt.xticks(rotation=45)
    plt.grid(True)

    # Set time axis for memory usage
    plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(interval=1))  # Every 1 minute
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # Plot disk usage
    plt.subplot(3, 1, 3)
    plt.plot(times, disk_usage, label='Disk Usage (%)', color='b')
    plt.title('Disk Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Disk Usage (%)')
    plt.xticks(rotation=45)
    plt.grid(True)

    # Set time axis for disk usage
    plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(interval=1))  # Every 1 minute
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # Adjust layout to make sure there’s enough space for labels
    plt.tight_layout()

    # Save the plot as a PNG file
    plt.savefig('resource_usage_plot.png')

    # Optionally, you can close the plot window to free up resources
    plt.close()

if __name__ == "__main__":
    plot_resources()

