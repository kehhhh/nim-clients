import os
import time
import sys
from typing import Iterator
import argparse
import grpc

sys.path.append(os.path.join(os.getcwd(), "../interfaces"))
# Importing gRPC compiler auto-generated maxine eyecontact library
from eye_contact import eyecontact_pb2, eyecontact_pb2_grpc


def generate_request_for_inference(input_filepath: os.PathLike, params: dict):
    """Generator to produce the request data stream
    Args:
      input_filepath: Path to input file
      params: Parameters for the feature
    """
    data_chunks = 64 * 1024  # bytes, we send the mp4 file in 64KB chunks
    if params:  # if params is supplied,
        # the first item in the input stream is a config object with parameters
        yield eyecontact_pb2.RedirectGazeRequest(config=eyecontact_pb2.RedirectGazeConfig(**params))
    with open(input_filepath, "rb") as fd:
        while True:
            buffer = fd.read(data_chunks)
            if buffer == b"":
                break
            yield eyecontact_pb2.RedirectGazeRequest(video_file_data=buffer)


def write_output_file_from_response(
    response_iter: Iterator[eyecontact_pb2.RedirectGazeResponse], output_filepath: os.PathLike
) -> None:
    """Function to write the output file from the incoming gRPC data stream.
    Args:
      response_iter: Responses from the server to write into output file
      output_filepath: Path to output file
    """
    with open(output_filepath, "wb") as fd:
        for response in response_iter:
            if response.HasField("video_file_data"):
                fd.write(response.video_file_data)


def parse_args():
    """
    Parse command-line arguments using argparse.
    """
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Process mp4 video files using gRPC" " and apply Gaze-redirection."
    )
    parser.add_argument(
        "--target",
        type=str,
        default="127.0.0.1:8004",
        help="The target gRPC server address.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="../assets/sample_input.mp4",
        help="The path to the input video file.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output.mp4",
        help="The path for the output video file.",
    )
    return parser.parse_args()


def main():
    """Main function to establish gRPC channel"""
    args = parse_args()

    input_filepath = args.input
    output_filepath = args.output
    params = {}
    if os.path.isfile(input_filepath):
        print(f"The file '{input_filepath}' exists. Proceeding with processing.")
    else:
        print(f"The file '{input_filepath}' does not exist. Exiting.")
        return

    # example of setting parameters
    # params = {"eye_size_sensitivity": 4, "detect_closure": 1 }
    with grpc.insecure_channel(target=args.target) as channel:
        try:
            stub = eyecontact_pb2_grpc.MaxineEyeContactServiceStub(channel)
            start_time = time.time()
            responses = stub.RedirectGaze(
                generate_request_for_inference(input_filepath=input_filepath, params=params)
            )
            if params:
                _ = next(responses)

            write_output_file_from_response(
                response_iter=responses, output_filepath=output_filepath
            )
            end_time = time.time()
            print(
                f"Function invocation completed in {end_time-start_time:.2f}s,"
                " the output file is generated."
            )
        except BaseException as e:
            print("An error occurred: %s", e)


if __name__ == "__main__":
    main()
