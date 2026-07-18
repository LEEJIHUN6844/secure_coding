import os

from market import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # 개발용 실행. 운영 시에는 gunicorn + eventlet 등 사용
    # (macOS는 AirPlay가 5000 포트를 점유하므로 PORT=5001 등으로 변경)
    port = int(os.environ.get("PORT", "5000"))
    socketio.run(
        app, host="127.0.0.1", port=port, debug=False, allow_unsafe_werkzeug=True
    )
