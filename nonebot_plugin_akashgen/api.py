import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import httpx
from nonebot import logger, get_plugin_config

from .config import Config

plugin_config = get_plugin_config(Config)


class JobStatus(Enum):
    """Job status enumeration."""
    WAITING = "waiting"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class GenerationRequest:
    """Image generation request."""
    prompt: str
    negative: str
    sampler: str
    scheduler: str
    preferred_gpu: Optional[list[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data: Dict[str, Any] = {
            "prompt": self.prompt,
            "negative": self.negative,
            "sampler": self.sampler,
            "scheduler": self.scheduler,
        }
        if self.preferred_gpu:
            data["preferred_gpu"] = self.preferred_gpu
        return data


@dataclass
class GenerationResponse:
    """Initial generation response."""
    job_id: str
    queue_position: int
    status: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationResponse":
        """Create from API response dictionary."""
        return cls(
            job_id=data["job_id"],
            queue_position=data["queue_position"],
            status=data["status"],
        )


@dataclass
class JobStatusResponse:
    """Job status response."""
    job_id: str
    worker_name: str
    worker_city: str
    worker_country: str
    status: str
    result: str
    worker_gpu: str
    elapsed_time: float
    queue_position: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobStatusResponse":
        """Create from API response dictionary."""
        return cls(
            job_id=data["job_id"],
            worker_name=data["worker_name"],
            worker_city=data["worker_city"],
            worker_country=data["worker_country"],
            status=data["status"],
            result=data["result"],
            worker_gpu=data["worker_gpu"],
            elapsed_time=data["elapsed_time"],
            queue_position=data["queue_position"],
        )


class AkashAPIError(Exception):
    """Base exception for Akash API errors."""
    pass


class AkashAPIClient:
    """Akash Network API client."""

    def __init__(self) -> None:
        self.base_url = plugin_config.akash_api_base_url
        self.timeout = plugin_config.akash_request_timeout
        self.max_retries = plugin_config.akash_max_retries
        self.poll_interval = plugin_config.akash_poll_interval
        
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response
                except httpx.HTTPError as e:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    if attempt == self.max_retries - 1:
                        raise AkashAPIError(f"Request failed after {self.max_retries} attempts: {e}")
                    await asyncio.sleep(1)  # Wait before retry
        
        raise AkashAPIError("Unexpected error in request handling")

    async def submit_generation_job(self, request: GenerationRequest) -> GenerationResponse:
        """Submit image generation job to Akash Network."""
        url = f"{self.base_url}/api/generate"
        
        logger.info(f"Submitting generation job with prompt: {request.prompt[:50]}...")
        
        try:
            response = await self._make_request(
                "POST",
                url,
                json=request.to_dict(),
                headers={"Content-Type": "application/json"}
            )
            
            data = response.json()
            logger.info(f"Job submitted successfully: {data['job_id']}")
            return GenerationResponse.from_dict(data)
            
        except Exception as e:
            logger.error(f"Failed to submit generation job: {e}")
            raise AkashAPIError(f"Failed to submit job: {e}")

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        """Get job status from Akash Network."""
        url = f"{self.base_url}/api/status"
        params = {"ids": job_id}
        
        try:
            response = await self._make_request("GET", url, params=params)
            data = response.json()
            
            if not data or not isinstance(data, list):
                raise AkashAPIError("Invalid status response format")
                
            return JobStatusResponse.from_dict(data[0])
            
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            raise AkashAPIError(f"Failed to get job status: {e}")

    async def wait_for_completion(
        self, 
        job_id: str, 
        max_wait_time: int = 300
    ) -> JobStatusResponse:
        """Wait for job completion with polling."""
        logger.info(f"Waiting for job {job_id} to complete...")
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                status_response = await self.get_job_status(job_id)
                
                if status_response.status == JobStatus.SUCCEEDED.value:
                    logger.info(f"Job {job_id} completed successfully")
                    return status_response
                    
                elif status_response.status == JobStatus.FAILED.value:
                    raise AkashAPIError(f"Job {job_id} failed")
                
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_wait_time:
                    raise AkashAPIError(f"Job {job_id} timed out after {max_wait_time} seconds")
                
                logger.debug(
                    f"Job {job_id} status: {status_response.status}, "
                    f"queue position: {status_response.queue_position}"
                )
                
                await asyncio.sleep(self.poll_interval)
                
            except AkashAPIError:
                raise
            except Exception as e:
                logger.error(f"Error while waiting for job completion: {e}")
                raise AkashAPIError(f"Error polling job status: {e}")

    async def fetch_generated_image(self, result_path: str) -> bytes:
        """Fetch the generated image."""
        # Build the full image URL
        image_url = f"{self.base_url}/_next/image"
        params = {
            "url": result_path,
            "w": "2048",
            "q": "100"
        }
        
        logger.info(f"Fetching generated image from: {result_path}")
        
        try:
            response = await self._make_request("GET", image_url, params=params)
            
            if response.headers.get("content-type", "").startswith("image/"):
                return response.content
            else:
                raise AkashAPIError("Response is not an image")
                
        except Exception as e:
            logger.error(f"Failed to fetch image: {e}")
            raise AkashAPIError(f"Failed to fetch image: {e}")

    async def generate_image(
        self,
        prompt: str,
        negative: str,
        sampler: str,
        scheduler: str,
    ) -> Tuple[bytes, JobStatusResponse]:
        """Complete image generation workflow."""
        # Create generation request
        request = GenerationRequest(
            prompt=prompt,
            negative=negative,
            sampler=sampler,
            scheduler=scheduler,
            preferred_gpu=plugin_config.akash_preferred_gpus,
        )
        
        # Submit job
        generation_response = await self.submit_generation_job(request)
        
        # Wait for completion
        status_response = await self.wait_for_completion(generation_response.job_id)
        
        # Fetch image
        image_data = await self.fetch_generated_image(status_response.result)
        
        return image_data, status_response


# Global API client instance
akash_client = AkashAPIClient()