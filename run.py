from app import create_app, db

# Inisialisasi aplikasi Flask
app = create_app()


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()  # Pastikan session dibersihkan setelah setiap request

if __name__ == '__main__':
    app.run(debug=True)