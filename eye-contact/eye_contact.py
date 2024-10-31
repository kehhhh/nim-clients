import os
from typing import Iterator
from interfaces.eye_contact import eyecontact_pb2

def generate_request_for_inference(
    input_filepath: os.PathLike = "input.mp4", params: dict = {}
) -> any:
    """Generator to produce the request data stream

    Args:
      input_filepath: Path to input file
      params: Parameters for the feature
    """
    DATA_CHUNKS = 64 * 1024  # bytes, we send the mp4 file in 64KB chunks
    if params:  # if params is supplied, the first item in the input stream is a config object with parameters
        yield eyecontact_pb2.RedirectGazeRequest(config=eyecontact_pb2.RedirectGazeConfig(**params))
    with open(input_filepath, "rb") as fd:
        while True:
            buffer = fd.read(DATA_CHUNKS)
            if buffer == b"":
                break
            yield eyecontact_pb2.RedirectGazeRequest(video_file_data=buffer)

def write_output_file_from_response(
    response_iter: Iterator[eyecontact_pb2.RedirectGazeResponse],
    output_filepath: os.PathLike = "output.mp4",
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