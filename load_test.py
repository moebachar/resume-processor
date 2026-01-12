"""
Load Testing Script for Resume Processor Microservice
Sends 100 requests in waves to test real-world scenario performance
"""

import asyncio
import aiohttp
import time
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any
import statistics
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SERVICE_URL = "https://resume-processor-57hessxqma-od.a.run.app/process"
API_KEY = os.getenv("API_SECRET_KEY", "dev-secret-key-12345")
INPUTS_DIR = Path("tests/inputs")
USER_JSON_PATH = Path("tests/user.json")
CONFIG_JSON_PATH = Path("tests/config.json")

# Load test configuration
REQUEST_WAVES = [
    {"delay": 0, "count": 50, "name": "Wave 1 (Initial Burst)"},
    {"delay": 1, "count": 20, "name": "Wave 2"},
    {"delay": 2, "count": 10, "name": "Wave 3"},
    {"delay": 3, "count": 10, "name": "Wave 4"},
    {"delay": 4, "count": 10, "name": "Wave 5"},
]

# Global results storage
results: List[Dict[str, Any]] = []


def load_user_data() -> Dict[str, Any]:
    """Load user.json file"""
    with open(USER_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_config_data() -> Dict[str, Any]:
    """Load config.json file"""
    with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_job_descriptions() -> List[str]:
    """Load job descriptions from YAML files in tests/inputs/"""
    job_texts = []
    yaml_files = sorted(INPUTS_DIR.glob("*.yaml"))[:100]  # Limit to 100 files

    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and 'text' in data:
                    job_texts.append(data['text'])
        except Exception as e:
            print(f"Warning: Failed to load {yaml_file}: {e}")

    if not job_texts:
        raise ValueError("No job descriptions found in tests/inputs/")

    print(f"[OK] Loaded {len(job_texts)} job descriptions from YAML files")
    return job_texts


async def send_request(
    session: aiohttp.ClientSession,
    request_id: int,
    job_text: str,
    user_json: Dict[str, Any],
    config_json: Dict[str, Any],
    wave_name: str
) -> Dict[str, Any]:
    """Send a single request to the API"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "job_text": job_text,
        "user_json": user_json,
        "config_json": config_json,
        "profile": "moderate"
    }

    request_start = time.time()
    result = {
        "request_id": request_id,
        "wave": wave_name,
        "status": None,
        "response_time": None,
        "success": False,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }

    try:
        async with session.post(SERVICE_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as response:
            response_time = time.time() - request_start
            result["response_time"] = round(response_time, 2)
            result["status"] = response.status

            if response.status == 200:
                response_data = await response.json()
                result["success"] = response_data.get("success", False)
                result["error"] = response_data.get("error")
            else:
                result["success"] = False
                error_text = await response.text()
                result["error"] = error_text[:200]  # Limit error message length

    except asyncio.TimeoutError:
        result["response_time"] = time.time() - request_start
        result["error"] = "Request timeout (>120s)"
    except Exception as e:
        result["response_time"] = time.time() - request_start
        result["error"] = str(e)[:200]

    return result


async def send_wave(
    wave_config: Dict[str, Any],
    job_texts: List[str],
    user_json: Dict[str, Any],
    config_json: Dict[str, Any],
    start_request_id: int
) -> List[Dict[str, Any]]:
    """Send a wave of concurrent requests"""

    wave_name = wave_config["name"]
    count = wave_config["count"]

    print(f"\n[WAVE] Starting {wave_name}: {count} requests")

    # Create session with connection pooling
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []

        for i in range(count):
            request_id = start_request_id + i
            # Cycle through job texts
            job_text = job_texts[request_id % len(job_texts)]

            task = send_request(
                session=session,
                request_id=request_id,
                job_text=job_text,
                user_json=user_json,
                config_json=config_json,
                wave_name=wave_name
            )
            tasks.append(task)

        # Execute all requests in parallel
        wave_results = await asyncio.gather(*tasks)

    return wave_results


async def run_load_test():
    """Execute the complete load test"""

    print("=" * 80)
    print("Resume Processor Microservice - Load Test")
    print("=" * 80)
    print(f"Service URL: {SERVICE_URL}")
    print(f"Total Requests: {sum(w['count'] for w in REQUEST_WAVES)}")
    print(f"Test Waves: {len(REQUEST_WAVES)}")
    print("=" * 80)

    # Load test data
    print("\n[SETUP] Loading test data...")
    job_texts = load_job_descriptions()
    user_json = load_user_data()
    config_json = load_config_data()
    print("[OK] Test data loaded successfully")

    # Track overall test timing
    test_start = time.time()
    request_id_counter = 0

    # Execute waves
    for wave in REQUEST_WAVES:
        # Wait for the specified delay
        if wave["delay"] > 0:
            await asyncio.sleep(wave["delay"])

        # Execute the wave
        wave_results = await send_wave(
            wave_config=wave,
            job_texts=job_texts,
            user_json=user_json,
            config_json=config_json,
            start_request_id=request_id_counter
        )

        results.extend(wave_results)
        request_id_counter += wave["count"]

        # Print wave summary
        successful = sum(1 for r in wave_results if r["success"])
        failed = len(wave_results) - successful
        avg_time = statistics.mean([r["response_time"] for r in wave_results if r["response_time"]])

        print(f"  [OK] {wave['name']} completed: {successful} success, {failed} failed, avg time: {avg_time:.2f}s")

    test_duration = time.time() - test_start

    # Print comprehensive results
    print_results_summary(test_duration)

    # Save detailed results to file
    save_results_to_file()


def print_results_summary(test_duration: float):
    """Print comprehensive test results"""

    print("\n" + "=" * 80)
    print("LOAD TEST RESULTS")
    print("=" * 80)

    # Overall statistics
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r["success"])
    failed_requests = total_requests - successful_requests

    print(f"\nOverall Statistics:")
    print(f"  Total Requests:     {total_requests}")
    print(f"  Successful:         {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
    print(f"  Failed:             {failed_requests} ({failed_requests/total_requests*100:.1f}%)")
    print(f"  Test Duration:      {test_duration:.2f}s")

    # Response time statistics (only for completed requests)
    response_times = [r["response_time"] for r in results if r["response_time"] is not None]

    if response_times:
        print(f"\nResponse Time Statistics:")
        print(f"  Min:                {min(response_times):.2f}s")
        print(f"  Max:                {max(response_times):.2f}s")
        print(f"  Mean:               {statistics.mean(response_times):.2f}s")
        print(f"  Median:             {statistics.median(response_times):.2f}s")
        if len(response_times) > 1:
            print(f"  Std Dev:            {statistics.stdev(response_times):.2f}s")

        # Percentiles
        sorted_times = sorted(response_times)
        p50 = sorted_times[int(len(sorted_times) * 0.50)]
        p90 = sorted_times[int(len(sorted_times) * 0.90)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]

        print(f"  P50 (median):       {p50:.2f}s")
        print(f"  P90:                {p90:.2f}s")
        print(f"  P95:                {p95:.2f}s")
        print(f"  P99:                {p99:.2f}s")

    # Status code distribution
    status_codes = {}
    for r in results:
        status = r.get("status") or "timeout/error"
        status_codes[status] = status_codes.get(status, 0) + 1

    print(f"\nStatus Code Distribution:")
    for status, count in sorted(status_codes.items()):
        print(f"  {status}: {count} ({count/total_requests*100:.1f}%)")

    # Wave-by-wave breakdown
    print(f"\nWave-by-Wave Breakdown:")
    for wave_config in REQUEST_WAVES:
        wave_name = wave_config["name"]
        wave_results = [r for r in results if r["wave"] == wave_name]
        wave_success = sum(1 for r in wave_results if r["success"])
        wave_failed = len(wave_results) - wave_success
        wave_times = [r["response_time"] for r in wave_results if r["response_time"] is not None]

        if wave_times:
            wave_avg = statistics.mean(wave_times)
            print(f"  {wave_name}:")
            print(f"    Success: {wave_success}/{len(wave_results)} ({wave_success/len(wave_results)*100:.1f}%)")
            print(f"    Avg Time: {wave_avg:.2f}s")

    # Error analysis
    errors = [r for r in results if r["error"]]
    if errors:
        print(f"\nError Analysis ({len(errors)} errors):")
        error_types = {}
        for r in errors:
            error_msg = r["error"][:50]  # First 50 chars
            error_types[error_msg] = error_types.get(error_msg, 0) + 1

        for error_msg, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  [{count}x] {error_msg}")

    print("\n" + "=" * 80)


def save_results_to_file():
    """Save detailed results to JSON file"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"load_test_results_{timestamp}.json"

    output_data = {
        "test_metadata": {
            "timestamp": datetime.now().isoformat(),
            "service_url": SERVICE_URL,
            "total_requests": len(results),
            "waves": REQUEST_WAVES
        },
        "results": results,
        "summary": {
            "total_requests": len(results),
            "successful_requests": sum(1 for r in results if r["success"]),
            "failed_requests": sum(1 for r in results if not r["success"]),
            "response_times": {
                "min": min([r["response_time"] for r in results if r["response_time"]]) if results else None,
                "max": max([r["response_time"] for r in results if r["response_time"]]) if results else None,
                "mean": statistics.mean([r["response_time"] for r in results if r["response_time"]]) if results else None,
            }
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVED] Detailed results saved to: {output_file}")


if __name__ == "__main__":
    try:
        asyncio.run(run_load_test())
    except KeyboardInterrupt:
        print("\n\n[WARNING] Test interrupted by user")
        if results:
            print_results_summary(0)
            save_results_to_file()
    except Exception as e:
        print(f"\n\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
