import pandas as pd
import numpy as np
import argparse

# Define initial constants (modifiable)
min_participation_time = 500
max_operational_time = 9000
max_active_devices = 400
deviation_factor = 0.5
min_continuous_run_time = 700
random_device_failure_probability = 0.02  # Probability of random device failure (2%)
failure_duration = 5  # Duration (in seconds) for which a device maintains the last power output


def allocate_power(input_file, output_file, min_participation_time, max_operational_time, deviation_factor,
                   optimize=False):
    df = pd.read_excel(input_file, engine="openpyxl")
    df.columns = df.columns.astype(str).str.strip()

    battery_capacities = pd.to_numeric(df.iloc[0, 2:].values, errors='coerce')
    power_outputs_positive = pd.to_numeric(df.iloc[1, 2:].values, errors='coerce')
    power_outputs_negative = pd.to_numeric(df.iloc[2, 2:].values, errors='coerce')

    num_devices = len(battery_capacities)
    df_power = df.iloc[4:].copy()
    psums = pd.to_numeric(df.iloc[4:, 1].values, errors='coerce')
    timestamps = df.iloc[4:, 0].values
    num_time_steps = min(len(psums), len(timestamps))
    psums = psums[:num_time_steps]
    timestamps = timestamps[:num_time_steps]
    df_power = df_power.iloc[:num_time_steps]

    device_matrix = np.zeros((num_time_steps, num_devices))
    device_active_time = np.zeros(num_devices)
    device_participation_time = np.zeros(num_devices)
    device_continuous_run_time = np.zeros(num_devices)
    device_max_continuous_run = np.zeros(num_devices)
    device_in_use = np.zeros(num_devices, dtype=bool)
    device_failure_time = np.zeros(num_devices)
    last_power_output = np.zeros(num_devices)

    # Ensure all devices participate equally over time
    for t in range(num_time_steps):
        required_power = psums[t]
        active_devices = np.zeros(num_devices)
        if required_power == 0:
            device_continuous_run_time[device_in_use] = 0
            continue

        # Sort devices by participation time to ensure all devices get a chance
        valid_devices = sorted(range(num_devices),
                               key=lambda idx: (device_participation_time[idx], -device_continuous_run_time[idx]))

        pmax_values = power_outputs_positive if required_power > 0 else power_outputs_negative
        power_sign = 1 if required_power > 0 else -1

        allocated_power = 0
        for idx in valid_devices:
            if allocated_power >= abs(required_power):
                break

            if device_active_time[idx] < max_operational_time:
                if np.random.rand() < random_device_failure_probability or device_failure_time[idx] > 0:
                    actual_power = last_power_output[idx]
                    device_failure_time[idx] = failure_duration if device_failure_time[idx] == 0 else \
                    device_failure_time[idx] - 1
                else:
                    max_possible_power = abs(pmax_values[idx])
                    min_possible_power = max_possible_power * (1 - deviation_factor)
                    actual_power = power_sign * np.random.uniform(min_possible_power * 0.9, max_possible_power * 1.1)
                    last_power_output[idx] = actual_power

                active_devices[idx] = round(actual_power, 12)
                allocated_power += abs(actual_power)
                device_active_time[idx] += 1
                device_participation_time[idx] += 1
                device_continuous_run_time[idx] += 1
                device_max_continuous_run[idx] = max(device_max_continuous_run[idx], device_continuous_run_time[idx])
                device_in_use[idx] = True
            else:
                device_in_use[idx] = False
                device_continuous_run_time[idx] = 0

        device_matrix[t, :] = active_devices

    df_output = pd.DataFrame(device_matrix, columns=df.columns[2:num_devices + 2])
    df_output.insert(0, "Psum", psums)
    df_output.insert(0, "Timestamp", timestamps)
    df_output["Error_Diff"] = df_output["Psum"] - df_output.iloc[:, 2:].sum(axis=1)
    df_output["Error_Diff"] += np.random.uniform(-0.5, 0.5, size=len(df_output))
    df_output.loc[df_output["Error_Diff"].abs() < 1e-3, "Error_Diff"] = 0

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
