FROM alpine:latest

# Set working directory
WORKDIR /app

# Add a script to control the runtime
COPY run.sh /app/run.sh

# Make the script executable
RUN chmod +x /app/run.sh

# Default command to run the script
ENTRYPOINT ["/app/run.sh"]