from flask import Flask, render_template, request, send_file, after_this_request
import os
import sys
import grpc
import tempfile

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import the eye_contact module
from eye_contact import generate_request_for_inference, write_output_file_from_response
from interfaces.eye_contact import eyecontact_pb2_grpc

app = Flask(__name__)
API_KEY = "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"
FUNCTION_ID = "15c6f1a0-3843-4cde-b5bc-803a4966fbb6"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'video' not in request.files:
            return 'No video file uploaded', 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return 'No selected file', 400

        # Validate file size
        if request.content_length > 100 * 1024 * 1024:  # 100MB limit
            return 'File too large. Maximum size is 100MB', 400

        # Create temporary files
        temp_input = None
        temp_output = None
        
        try:
            # Save uploaded file temporarily
            temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_input_path = temp_input.name
            video_file.save(temp_input_path)
            temp_input.close()
            
            # Validate that the saved file is actually an MP4
            if not is_valid_mp4(temp_input_path):
                raise ValueError("Invalid MP4 file format")
            
            # Set up output path
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_output_path = temp_output.name
            temp_output.close()
            
            # Set up gRPC channel
            credentials = grpc.ssl_channel_credentials()
            metadata = [
                ('authorization', f'Bearer {API_KEY}'),
                ('function-id', FUNCTION_ID)
            ]
            
            with grpc.secure_channel('grpc.nvcf.nvidia.com:443', credentials) as channel:
                stub = eyecontact_pb2_grpc.MaxineEyeContactServiceStub(channel)
                
                # Generate request and get response
                request_iterator = generate_request_for_inference(temp_input_path)
                response_iterator = stub.RedirectGaze(
                    request_iterator=request_iterator,
                    metadata=metadata
                )
                
                # Write output file
                write_output_file_from_response(response_iterator, temp_output_path)
                
                # Verify the output file was created and is valid
                if not os.path.exists(temp_output_path) or os.path.getsize(temp_output_path) == 0:
                    raise ValueError("Failed to generate output video")

                # Register cleanup function to run after request
                @after_this_request
                def cleanup(response):
                    cleanup_files(temp_input_path, temp_output_path)
                    return response
                
                return send_file(
                    temp_output_path,
                    as_attachment=True,
                    download_name='processed_video.mp4',
                    mimetype='video/mp4'
                )
                
        except grpc.RpcError as e:
            error_message = f"API Error: {e.details() if hasattr(e, 'details') else str(e)}"
            app.logger.error(error_message)
            cleanup_files(
                temp_input_path if temp_input else None,
                temp_output_path if temp_output else None
            )
            return error_message, 500
            
        except Exception as e:
            error_message = f"Processing Error: {str(e)}"
            app.logger.error(error_message)
            cleanup_files(
                temp_input_path if temp_input else None,
                temp_output_path if temp_output else None
            )
            return error_message, 500
    
    return render_template('index.html')

def is_valid_mp4(filepath):
    """Basic validation of MP4 file format"""
    try:
        with open(filepath, 'rb') as f:
            # Check for MP4 file signature
            header = f.read(8)
            return header[4:8] in (b'ftyp', b'moov')
    except Exception:
        return False

def cleanup_files(*files):
    """Helper function to safely delete temporary files"""
    for file in files:
        if file and os.path.exists(file):
            try:
                os.unlink(file)
            except Exception as e:
                app.logger.error(f"Error deleting temporary file {file}: {e}")

if __name__ == '__main__':
    app.run(debug=True)