#!/bin/bash
# =============================================================================
# Geopard Web Server - Startup Script
# =============================================================================
# This script ensures all dependencies are installed and configured before
# starting the web server with full MCP integration.
#
# Usage:
#   ./start_server.sh [--port PORT] [--dev]
#
# Options:
#   --port PORT    Server port (default: 8000)
#   --dev          Development mode with auto-reload
#   --help         Show this help message
#
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
PORT=8000
DEV_MODE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --help)
            head -n 18 "$0" | tail -n +2 | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# =============================================================================
# Helper Functions
# =============================================================================

print_banner() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  🌍 Geopard Web Server - Kanton Luzern Geodaten Assistant${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}▶${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

check_python() {
    print_step "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.8 or higher."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION detected"
}

check_venv() {
    print_step "Checking virtual environment..."
    
    if [ ! -d "$SCRIPT_DIR/venv" ]; then
        print_warning "Virtual environment not found. Creating one..."
        python3 -m venv "$SCRIPT_DIR/venv"
        print_success "Virtual environment created"
    else
        print_success "Virtual environment exists"
    fi
    
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate"
    print_success "Virtual environment activated"
}

install_dependencies() {
    print_step "Installing/updating dependencies..."
    
    # Upgrade pip
    pip install --upgrade pip --quiet
    
    # Install core dependencies
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
        print_success "Core dependencies installed"
    fi
    
    # Install FastAPI dependencies for web server
    pip install fastapi uvicorn[standard] --quiet
    print_success "Web server dependencies installed"
    
    # Install MCP dependencies
    pip install mcp --quiet
    print_success "MCP dependencies installed"
    
    if [ "$DEV_MODE" = true ]; then
        if [ -f "$SCRIPT_DIR/requirements-dev.txt" ]; then
            pip install -r "$SCRIPT_DIR/requirements-dev.txt" --quiet
            print_success "Development dependencies installed"
        fi
    fi
}

check_env_file() {
    print_step "Checking environment configuration..."
    
    ENV_FILE="$SCRIPT_DIR/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Environment file .env not found"
        
        # Check for example file
        if [ -f "$SCRIPT_DIR/backend/.env.example" ]; then
            echo -e "${YELLOW}Creating .env from template...${NC}"
            cp "$SCRIPT_DIR/backend/.env.example" "$ENV_FILE"
            
            print_error "IMPORTANT: Please edit .env with your Azure credentials:"
            echo "  - AZURE_OPENAI_API_KEY"
            echo "  - AZURE_OPENAI_ENDPOINT"
            echo "  - AZURE_SEARCH_ENDPOINT"
            echo "  - AZURE_SEARCH_KEY"
            echo ""
            echo "Then run this script again."
            exit 1
        else
            print_error "No .env.example found. Please create .env manually."
            exit 1
        fi
    fi
    
    # Validate critical environment variables
    source "$ENV_FILE"
    
    MISSING_VARS=()
    
    [ -z "$AZURE_OPENAI_API_KEY" ] && MISSING_VARS+=("AZURE_OPENAI_API_KEY")
    [ -z "$AZURE_OPENAI_ENDPOINT" ] && MISSING_VARS+=("AZURE_OPENAI_ENDPOINT")
    [ -z "$AZURE_SEARCH_ENDPOINT" ] && MISSING_VARS+=("AZURE_SEARCH_ENDPOINT")
    [ -z "$AZURE_SEARCH_KEY" ] && MISSING_VARS+=("AZURE_SEARCH_KEY")
    
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        print_error "Missing required environment variables in .env:"
        for var in "${MISSING_VARS[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    print_success "Environment configuration valid"
}

test_azure_connection() {
    print_step "Testing Azure connections..."
    
    # Test Azure OpenAI
    python3 -c "
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

try:
    client = AzureOpenAI(
        api_key=os.getenv('AZURE_OPENAI_API_KEY'),
        api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview'),
        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
    )
    # Quick test with minimal tokens
    client.embeddings.create(input='test', model=os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large'))
    print('✓ Azure OpenAI connection OK')
except Exception as e:
    print(f'✗ Azure OpenAI connection failed: {e}')
    exit(1)
" || {
        print_error "Azure OpenAI connection test failed"
        exit 1
    }
    
    # Test Azure Search
    python3 -c "
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

try:
    client = SearchClient(
        endpoint=os.getenv('AZURE_SEARCH_ENDPOINT'),
        index_name=os.getenv('AZURE_SEARCH_INDEX_NAME', 'geopard-rag-v2'),
        credential=AzureKeyCredential(os.getenv('AZURE_SEARCH_KEY'))
    )
    # Test search
    results = list(client.search('test', top=1))
    print('✓ Azure Search connection OK')
except Exception as e:
    print(f'✗ Azure Search connection failed: {e}')
    exit(1)
" || {
        print_error "Azure Search connection test failed"
        exit 1
    }
    
    print_success "All Azure connections working"
}

check_port() {
    print_step "Checking if port $PORT is available..."
    
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $PORT is already in use"
        
        # Try to kill existing process
        PID=$(lsof -ti:$PORT)
        if [ -n "$PID" ]; then
            echo -e "${YELLOW}Attempting to stop existing server (PID: $PID)...${NC}"
            kill -9 $PID 2>/dev/null || true
            sleep 2
            
            if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
                print_error "Could not free port $PORT. Please stop the process manually."
                exit 1
            fi
            print_success "Existing server stopped"
        fi
    else
        print_success "Port $PORT is available"
    fi
}

start_server() {
    print_step "Starting Geopard Web Server with MCP..."
    
    cd "$SCRIPT_DIR/frontend"
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🚀 Server Configuration:${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "  📍 URL:           ${GREEN}http://localhost:$PORT${NC}"
    echo -e "  📚 API Docs:      ${GREEN}http://localhost:$PORT/docs${NC}"
    echo -e "  💬 Chat UI:       ${GREEN}http://localhost:$PORT${NC}"
    echo -e "  🏥 Health Check:  ${GREEN}http://localhost:$PORT/health${NC}"
    echo -e "  🔧 MCP Tools:     ${GREEN}http://localhost:$PORT/tools${NC}"
    echo -e "  🗄️  RAG System:    ${GREEN}Enabled (Azure AI Search)${NC}"
    echo -e "  📦 Mode:          ${GREEN}$([ "$DEV_MODE" = true ] && echo "Development (auto-reload)" || echo "Production")${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ "$DEV_MODE" = true ]; then
        uvicorn chat_server_mcp:app --host 0.0.0.0 --port $PORT --reload
    else
        uvicorn chat_server_mcp:app --host 0.0.0.0 --port $PORT
    fi
}

cleanup() {
    echo ""
    print_warning "Shutting down server..."
    
    # Kill any remaining processes
    pkill -f "uvicorn chat_server" || true
    pkill -f "chat_server_mcp" || true
    
    print_success "Server stopped"
    exit 0
}

# =============================================================================
# Main Execution
# =============================================================================

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run startup checks
print_banner

check_python
check_venv
install_dependencies
check_env_file
test_azure_connection
check_port

# Start the server
start_server
