# Car Parts Search Assistant

Car Parts Search Assistant is a web application that allows users to search for car parts by either entering a query or uploading a file. The application consists of two main components:

1. **Backend**: A Python FastAPI backend that handles the search queries and file uploads.
2. **Frontend**: A React application that provides the user interface for searching car parts.

## Folder Structure
carparts-assistant/ 
│ 
├── backend/ # Python backend using FastAPI 
│ 
├── main.py # Main application entry point for FastAPI 
│ 
├── requirements.txt # Python dependencies 
│ └── ... # Other backend files and folders 
│ ├── daparto-assistant/ # React frontend application 
│ 
├── src/ # Source code for React components 
│ 
├── public/ # Public assets 
│ 
├── package.json # npm dependencies and scripts 
│ └── ... # Other frontend files and folders 
│ 
└── README.md # Project documentation


## Prerequisites

- **Python 3.8+** for the backend.
- **Node.js (v14+) and npm/yarn** for the frontend.

## Getting Started

### Backend Setup

1. Navigate to the `backend` directory:

    ```bash
    cd backend
    ```

2. Create a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Run the backend server:

    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8010
    ```

   The backend should now be running on `http://localhost:8010`.

### Frontend Setup

1. Navigate to the `daparto-assistant` directory:

    ```bash
    cd daparto-assistant
    ```

2. Install the dependencies:

    ```bash
    npm install
    # or
    yarn install
    ```

3. Start the frontend development server:

    ```bash
    npm start
    # or
    yarn start
    ```

   The frontend should now be running on `http://localhost:3000`.

## Running the Full Application

To run the application, make sure both the backend and frontend servers are running simultaneously. Note the ports will be whatever you want them to be :)

- **Backend**: `http://localhost:8010`
- **Frontend**: `http://localhost:3000`

You can now access the application on your browser at `http://localhost:3000`.

## File Upload and Search Functionality

- Enter a search query or upload a file using the search form on the frontend.
- The backend processes the search request and returns results, which are then displayed in the UI.

## Development and Contributing

Feel free to contribute to this project by forking the repository and creating pull requests.

## License

This project is licensed under do-whatever-you-want-with-it license :)


