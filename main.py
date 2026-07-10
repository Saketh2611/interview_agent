from fastapi import FastAPI

from src.interview_router import router as interview_router

app = FastAPI(title="Interview Agent")
app.include_router(interview_router)


def main():
    print("Interview agent API is ready.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
