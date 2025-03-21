from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from format_txt_history_full import (
    chunk_messages,
    detect_file,
    normalize_phone_number,
    parse_messages,
    run_imessage_exporter,
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/export", methods=["POST"])
async def export_messages():
    try:
        name = request.form.get("name")
        phone_number = request.form.get("phone_number")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        if not name or not phone_number:
            return jsonify(
                {
                    "status": "error",
                    "message": "Please enter both a name and phone number",
                },
            ), 400

        # Normalize the phone number
        try:
            normalized_phone = normalize_phone_number(phone_number)
        except Exception:
            return jsonify(
                {
                    "status": "error",
                    "message": "Please enter a valid phone number (e.g., +1234567890 or 123-456-7890)",
                },
            ), 400

        # Create output directory if it doesn't exist
        base_output_folder = Path("output")
        base_output_folder.mkdir(exist_ok=True)

        try:
            # Run the export using existing logic
            await run_imessage_exporter(
                name=name,
                date=start_date,
                phone_number=normalized_phone,
                imessage_filter="",
                end_date=end_date,
            )
        except FileNotFoundError:
            return jsonify(
                {
                    "status": "error",
                    "message": "No messages found for this contact. Please check the name and phone number.",
                },
            ), 404
        except Exception as e:
            return jsonify(
                {
                    "status": "error",
                    "message": f"There was a problem accessing the messages: {e!s}",
                },
            ), 500

        try:
            # Process the messages using existing logic
            input_file = detect_file(base_output_folder, normalized_phone)
            messages = parse_messages(input_file, name)
            output_dir = chunk_messages(messages, base_output_folder, size_mb=5)

            # Get the list of generated files
            files = []
            for file in output_dir.glob("*"):
                if file.is_file():
                    files.append(file.name)

            return jsonify(
                {
                    "status": "success",
                    "message": f"Successfully exported messages for {name}",
                    "files": files,
                    "output_directory": str(output_dir),
                },
            )

        except Exception as e:
            return jsonify({"status": "error", "message": f"Error processing messages: {e!s}"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": f"Unexpected error: {e!s}"}), 500


@app.route("/download/<path:filename>")
def download_file(filename):
    try:
        directory = Path("output")
        current_directory = os.path.abspath(os.curdir)  # import os
        requested_path = os.path.abspath(directory / filename)
        common_prefix = os.path.commonprefix([requested_path, current_directory])
        if common_prefix != current_directory:
            raise Exception(f"Invalid path: {filename}. It is outside of the current directory.")
        return send_file(directory / filename, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error downloading file: {e!s}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
