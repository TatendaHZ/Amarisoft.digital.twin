import psutil
import time
import csv

# Function to monitor CPU, Memory, and Disk usage and save to CSV file
def monitor_resources():
    # Open the CSV file in append mode
    with open("resource_usage.csv", mode="a", newline="") as file:
        writer = csv.writer(file)

        # Write header if the file is empty
        if file.tell() == 0:
            writer.writerow(["Time", "CPU (%)", "Memory (%)", "Disk Usage (%)"])

        # Monitor the resources
        while True:
            # Get current time
            current_time = time.strftime("%H:%M:%S")

            # Get CPU usage percentage
            cpu_usage = psutil.cpu_percent(interval=1)

            # Get Memory usage percentage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            # Get Disk usage percentage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent

            # Write the resource usage data to the CSV file
            writer.writerow([current_time, cpu_usage, memory_usage, disk_usage])
            file.flush()  # Ensure immediate write to file

            # Pause for 1 second before taking the next reading
            time.sleep(1)

if __name__ == "__main__":
    try:
        monitor_resources()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

