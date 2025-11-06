#!/bin/bash

# Ubuntu Systemd Docker Container Management Script

function show_help() {
    echo "Ubuntu Systemd Docker Container Management"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build    - Build the Ubuntu systemd Docker image"
    echo "  run      - Run the container using docker-compose"
    echo "  start    - Start existing container"
    echo "  stop     - Stop the container"
    echo "  restart  - Restart the container"
    echo "  shell    - Access container shell"
    echo "  logs     - Show container logs"
    echo "  status   - Show container status"
    echo "  clean    - Remove container and image"
    echo "  help     - Show this help message"
}

function build_image() {
    echo "Building Ubuntu systemd Docker image..."
    sudo docker compose build
}

function run_container() {
    echo "Starting Ubuntu systemd container..."
    sudo docker compose up -d
    echo "Container started. Use '$0 shell' to access it."
}

function start_container() {
    echo "Starting existing container..."
    sudo docker compose start
}

function stop_container() {
    echo "Stopping container..."
    sudo docker compose stop
}

function restart_container() {
    echo "Restarting container..."
    sudo docker compose restart
}

function access_shell() {
    echo "Accessing container shell..."
    sudo docker exec -it ubuntu-systemd /bin/bash
}

function show_logs() {
    echo "Showing container logs..."
    sudo docker compose logs -f
}

function show_status() {
    echo "Container status:"
    sudo docker compose ps
    echo ""
    echo "Systemd status inside container:"
    sudo docker exec ubuntu-systemd systemctl status 2>/dev/null || echo "Container not running or systemd not accessible"
}

function clean_up() {
    echo "Cleaning up container and image..."
    sudo docker compose down
    sudo docker rmi venkat73-ubuntu-systemd 2>/dev/null || echo "Image not found"
    echo "Cleanup complete."
}

case "$1" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    shell)
        access_shell
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    clean)
        clean_up
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for available commands."
        exit 1
        ;;
esac
