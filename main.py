from app import create_app

# The app instance is created by the factory function
app = create_app()

if __name__ == '__main__':
    # This block is for local development, not for Gunicorn
    app.run(host='0.0.0.0', port=8000, debug=True)