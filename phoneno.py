start_num = "0800000000"
end_num = "0999999999"

# Open the text file for writing
with open("output.txt", "w") as file:
    for num in range(int(start_num), int(end_num) + 1):
        formatted_num = str(num).zfill(10)  # Pad with leading zeros to maintain 10 digits
        file.write(formatted_num + "\n")  # Write each number followed by a newline

print("Numbers written to output.txt successfully!")
