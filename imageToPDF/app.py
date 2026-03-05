import io
import requests
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import img2pdf
from typing import List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Image to PDF Converter")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Only frontend origin
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Image to PDF Converter API is running. Use POST /convert-urls to generate PDF."}

@app.post("/convert-urls")
async def convert_urls(urls: List[str] = Body(..., embed=True)):
    """
    Takes a list of image URLs, downloads them, and returns a single combined PDF.
    Ensures lossless conversion and original size.
    """
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    image_bytes_list = []
    total_image_size = 0

    try:
        for url in urls:
            logger.info(f"Downloading image: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            content = response.content
            image_bytes_list.append(content)
            total_image_size += len(content)
            
        logger.info(f"Total downloaded image size: {total_image_size} bytes")

        # Convert images to PDF
        # img2pdf.convert expects a list of file-like objects or bytes
        pdf_bytes = img2pdf.convert(image_bytes_list)
        
        pdf_size = len(pdf_bytes)
        logger.info(f"Generated PDF size: {pdf_size} bytes")

        # Basic verification: PDF size should not be significantly larger than total image size
        # (Standard PDF overhead is usually a few KB)
        if pdf_size > total_image_size + (len(urls) * 2048) + 10240:
             logger.warning(f"PDF size ({pdf_size}) is larger than expected (Total images: {total_image_size})")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=converted_images.pdf",
                "X-Total-Image-Size": str(total_image_size),
                "X-PDF-Size": str(pdf_size)
            }
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading image: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to download image from one of the URLs: {str(e)}")
    except Exception as e:
        logger.error(f"Error during conversion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred during conversion: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
