

def seconds_to_time(seconds):

    if seconds < 0:
        raise ValueError("Error.")

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    return f"{minutes}:{remaining_seconds:02d}"

seconds = 295
formatted_time = seconds_to_time(seconds)
print(f"Time: {formatted_time}")



