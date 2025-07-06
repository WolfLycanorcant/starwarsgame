@echo on
echo Starting Star Wars Bridge Simulator...
echo.

:: Check if Python is installed
python --version
echo.

:: Create and activate virtual environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate

:: Install dependencies
echo Installing required packages...
pip install -r requirements.txt

:: Check if Flask is installed correctly
echo.
echo Checking Flask installation...
python -c "import flask"

:: Start the Flask server
echo.
echo Starting server...
python app.py
