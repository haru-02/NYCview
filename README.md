# NYCview

## A jaunt assessment.

This is a simple agent that fetches location names from a file in the project and
queries the usnplash api, scoring the images with metadata and finally aggregating the best results.

## Reasoning and Architecture:

The design choices and the architecture of code is explained [here](./NYCview.md)

## Getting Started:

To run the project, please have the latest version of docker and docker compose installed.

### Launch the environment:

First, ensure that you have filled in your unsplash api access key in the `docker-compose.yml` file.

Ten different locations of nyc are specified in the `locations.json` file. you can change them or add more if you would like to view different places.

run the following commmand to observe the output.

```bash
docker compose up --build
```

### Access the ouput

The images and the metadata for each location is available in the output folder generated.

## Tech Stack:

- Requests for python requests.
- pydantic for basemodel - protects the data typing that is returned from api.

## Image Source:

Special thanks to [unsplash](https://unsplash.com/) api for providing free license images for this project.
