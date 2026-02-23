import pandas as pd
import numpy as np
import argparse

# Define initial constants (modifiable)
min_participation_time = 500  # Minimum time (in seconds) each device must participate
max_operational_time = 9000  # Increased to allow more devices to participate over time
max_active_devices = 400  # Increased to allow more devices to participate simultaneously
deviation_factor = 0.5  # Deviation allowed, strictly reducing Pmax or increasing -Pmax
min_continuous_run_time = 700  # Minimum continuous run time in seconds for each device
random_device_failure_probability = 0.02  # Probability of random device failure (2%)
failure_duration = 5  # Duration (in seconds) for which a device outputs zero during a failure


def allocate_power(input_file, output_file, min_participation_time, max_operational_time, deviation_factor, optimize=False):
    # Load the input Excel file
    df = pd.read_excel(input_file, engine="openpyxl")

    # Convert all column names to strings
    df.columns = df.columns.astype(str).str.strip()

    # Extract battery capacities, power outputs, and negative power outputs
    battery_capacities = pd.to_numeric(df.iloc[0, 2:].values, errors='coerce')
    power_outputs_positive = pd.to_numeric(df.iloc[1, 2:].values, errors='coerce')
    power_outputs_negative = pd.to_numeric(df.iloc[2, 2:].values, errors='coerce')

    num_devices = len(battery_capacities)

    # Extract power distribution data from row 4 onwards
    df_power = df.iloc[4:].copy()

    # Extract Psum values from Column B (Index 1)
    psums = pd.to_numeric(df.iloc[4:, 1].values, errors='coerce')

    # Extract timestamps dynamically and ensure it matches the number of time steps
    timestamps = df.iloc[4:, 0].values
    num_time_steps = min(len(psums), len(timestamps))
    psums = psums[:num_time_steps]
    timestamps = timestamps[:num_time_steps]
    df_power = df_power.iloc[:num_time_steps]

    # Initialize matrix for device allocations
    device_matrix = np.zeros((num_time_steps, num_devices))

    # Track active operation time, participation, and continuous run time for each device
    device_active_time = np.zeros(num_devices)
    device_participation_time = np.zeros(num_devices)
    device_continuous_run_time = np.zeros(num_devices)
    device_max_continuous_run = np.zeros(num_devices)  # Track maximum continuous run time
    device_in_use = np.zeros(num_devices, dtype=bool)  # Track active devices
    device_failure_time = np.zeros(num_devices)  # Track failure duration for each device

    # Random device failure simulation
    failed_devices = np.random.rand(num_devices) < random_device_failure_probability

    # Ensure all devices meet minimum participation time
    devices_meeting_min_time = np.zeros(num_devices, dtype=bool)

    # Fully randomize the device order to ensure distribution can start from any position
    randomized_device_order = np.random.permutation(num_devices)

    # Distribute power ensuring continuous operation until operation time is met
    for t in range(num_time_steps):
        required_power = psums[t]
        active_devices = np.zeros(num_devices)

        if required_power == 0:
            device_continuous_run_time[device_in_use] = 0  # Reset continuous run time if device is inactive
            continue  # If no power is required, keep the row as zeros

        if required_power > 0:
            valid_devices = [idx for idx in randomized_device_order if power_outputs_positive[idx] > 0]
            pmax_values = power_outputs_positive
            power_sign = 1
        else:
            valid_devices = [idx for idx in randomized_device_order if power_outputs_negative[idx] < 0]
            pmax_values = power_outputs_negative
            power_sign = -1

        if not valid_devices and required_power < 0:
            print(f"⚠️ Warning: Negative Psum at row {t+4}, but no devices assigned negative power!")

        # Maintain continuity: Prioritize devices with continuous run below minimum
        under_continuous_devices = [idx for idx in valid_devices if device_continuous_run_time[idx] < min_continuous_run_time]
        continuing_devices = [idx for idx in valid_devices if device_in_use[idx] and idx not in under_continuous_devices]
        new_devices = [idx for idx in valid_devices if not device_in_use[idx]]

        # Weighted allocation prioritizing under-participated and under-continuous devices
        weighted_devices = sorted(new_devices, key=lambda idx: (device_participation_time[idx] / min_participation_time, device_continuous_run_time[idx]))
        other_new_devices = [idx for idx in new_devices if idx not in weighted_devices]

        # Prioritize under-participated and under-continuous devices when power is insufficient
        prioritized_devices = under_continuous_devices + weighted_devices + continuing_devices + other_new_devices
        valid_devices = prioritized_devices[:max_active_devices]

        allocated_power = 0

        for idx in valid_devices:
            if allocated_power >= abs(required_power):
                break  # Stop allocation when Psum requirement is met

            if device_active_time[idx] < max_operational_time:  # Check against max operational time
                if failed_devices[idx] or device_failure_time[idx] > 0:
                    actual_power = 0
                    device_failure_time[idx] = failure_duration if device_failure_time[idx] == 0 else device_failure_time[idx] - 1
                else:
                    max_possible_power = abs(pmax_values[idx])
                    min_possible_power = max_possible_power * (1 - deviation_factor)
                    actual_power = power_sign * np.random.uniform(min_possible_power, max_possible_power)

                active_devices[idx] = round(actual_power, 12)

                allocated_power += abs(actual_power)
                device_active_time[idx] += 1
                device_participation_time[idx] += 1  # Track participation
                device_continuous_run_time[idx] += 1  # Track continuous run time
                device_max_continuous_run[idx] = max(device_max_continuous_run[idx], device_continuous_run_time[idx])
                device_in_use[idx] = True  # Mark as active

                # Mark device as having met minimum participation time if applicable
                if device_participation_time[idx] >= min_participation_time:
                    devices_meeting_min_time[idx] = True
            else:
                device_in_use[idx] = False  # Mark as inactive
                device_continuous_run_time[idx] = 0  # Reset continuous run time if device becomes inactive

        # Assign allocated power values
        device_matrix[t, :] = active_devices

    # Check for devices that did not meet minimum continuous run time
    devices_not_meeting_continuous_time = [idx + 1 for idx, run_time in enumerate(device_max_continuous_run) if run_time < min_continuous_run_time]
    if devices_not_meeting_continuous_time:
        print(f"⚠️ Devices that did not meet the minimum continuous run time of {min_continuous_run_time} seconds: {devices_not_meeting_continuous_time}")
    else:
        print(f"🔹 All devices met the minimum continuous run time of {min_continuous_run_time} seconds.")

    # Check for devices that did not meet minimum participation time
    unmet_devices_count = 0
    for idx in range(num_devices):
        if not devices_meeting_min_time[idx]:
            unmet_devices_count += 1
            if not optimize:
                print(f"⚠️ Warning: Device {idx+1} did not meet the minimum participation time of {min_participation_time} seconds.")

    if optimize:
        return unmet_devices_count

    print(f"🔹 Total devices that did not meet the minimum participation time: {unmet_devices_count}")

    # Create the final output DataFrame
    df_output = pd.DataFrame(device_matrix, columns=df.columns[2:num_devices + 2])

    # Add Timestamp and Psum columns back
    df_output.insert(0, "Psum", psums)
    df_output.insert(0, "Timestamp", timestamps)

    # **Calculate `Error_Diff`**
    df_output["Error_Diff"] = df_output["Psum"] - df_output.iloc[:, 2:].sum(axis=1)

    # **Set Error_Diff close to zero if within 1e-3 threshold**
    df_output.loc[df_output["Error_Diff"].abs() < 1e-3, "Error_Diff"] = 0

    # **Print max/min deviation**
    max_error_diff = df_output["Error_Diff"].max()
    min_error_diff = df_output["Error_Diff"].min()
    print(f"🔹 Max Deviation: {max_error_diff:.12f}")
    print(f"🔹 Min Deviation: {min_error_diff:.12f}")

    # Save updated data to Excel
    df_output.to_excel(output_file, index=False)
    print(f"✅ Power allocation completed. File saved as: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Allocate power based on device operation times.")
    parser.add_argument("input_file", type=str, nargs="?", default="example_input_small.xlsx",
                        help="Path to the input Excel file.")
    parser.add_argument("output_file", type=str, nargs="?", default="allocated_power.xlsx",
                        help="Path to save the output Excel file.")

    args = parser.parse_args()
    allocate_power(args.input_file, args.output_file, min_participation_time, max_operational_time, deviation_factor)
