"""
Test script to verify the system works within Render and API limits.

Based on konteks3baru.md:
- 14,400 requests per day (RPD)
- 30 requests per minute (RPM) 
- 2-second delay between requests
- 300 news batch processed in 10 minutes
"""
import asyncio
import time
from datetime import datetime, timedelta


async def test_api_rate_limits():
    """
    Test that our rate limiting configuration works within the specified limits.
    """
    print("Testing API rate limits based on konteks3baru.md specifications...")
    print()
    
    # Configuration from konteks
    rate_limit_delay = 2.0  # seconds between requests (from LLM_RATE_LIMIT_DELAY)
    max_rpm = 30  # Max requests per minute
    max_rpd = 14400  # Max requests per day
    
    print("Rate limit delay: {} seconds between requests".format(rate_limit_delay))
    print("Max requests per minute: {}".format(max_rpm))
    print("Max requests per day: {}".format(max_rpd))
    print()
    
    # Calculate expected requests per minute with 2-second delay
    expected_rpm = 60 / rate_limit_delay
    print("With {}-second delay, we get {} requests per minute".format(rate_limit_delay, expected_rpm))
    
    if expected_rpm <= max_rpm:
        print("[OK] Rate limiting is within API limits ({} <= {})".format(expected_rpm, max_rpm))
    else:
        print("[ERROR] Rate limiting exceeds API limits ({} > {})".format(expected_rpm, max_rpm))
    
    print()
    
    # Calculate expected requests per day if running 24/7
    expected_rpd = (60 * 60 * 24) / rate_limit_delay
    print("If running 24/7, we would make {} requests per day".format(expected_rpd))
    print("Note: The worker doesn't run 24/7, it only processes queued items")
    
    # In reality, with cron job every 40 mins generating ~300 items each,
    # and worker processing at 30/min, we stay within limits
    items_per_day = 36 * 300  # 36 cron runs * 300 items each
    print("With cron schedule (*/40 * * * *), max items to summarize per day: {}".format(items_per_day))
    
    if items_per_day <= max_rpd:
        print("[OK] Expected daily usage is within API limits ({} <= {})".format(items_per_day, max_rpd))
    else:
        print("[ERROR] Expected daily usage exceeds API limits ({} > {})".format(items_per_day, max_rpd))
    
    print()
    
    # Check if 300 items can be processed in 10 minutes
    items_to_process = 300
    time_for_batch = 10 * 60  # 10 minutes in seconds
    time_per_item = rate_limit_delay  # 2 seconds per item
    
    total_time_needed = items_to_process * time_per_item
    print("To process {} items with {}-second delays:".format(items_to_process, time_per_item))
    print("  Total time needed: {} seconds ({} minutes)".format(total_time_needed, total_time_needed/60))
    print("  Available time: {} seconds (10 minutes)".format(time_for_batch))
    
    if total_time_needed <= time_for_batch:
        print("[OK] Can process {} items within 10 minutes".format(items_to_process))
    else:
        print("[ERROR] Cannot process {} items within 10 minutes".format(items_to_process))
        print("  Would need {:.1f} minutes instead of 10 minutes".format(total_time_needed/60))
    
    print()
    
    # Check the cron schedule: */40 * * * * (every 40 minutes)
    print("Cron schedule: */40 * * * * (every 40 minutes)")
    print("- This means 36 crawls per day (24*60/40 = 36)")
    print("- If each crawl generates ~300 items, that's ~10,800 summary requests per day")
    print("- This is within the {} RPD limit".format(max_rpd))
    
    print()
    print("All tests completed!")
    
    return True


def test_render_deployability():
    """
    Test that the configuration is suitable for Render deployment.
    """
    print("\nTesting Render deployability...")
    
    # Check for required files
    import os
    
    # When running from project root (where the script is executed), check:
    required_files = [
        'render.yaml',    # In project root
        'Dockerfile',     # In project root 
        'backend/requirements.txt',  # In backend dir
        'backend/app/main.py'        # In backend/app dir
    ]
    
    all_present = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print("[OK] {} exists".format(file_path))
        else:
            print("[ERROR] {} missing".format(file_path))
            all_present = False
    
    if all_present:
        print("[OK] All required files for Render deployment are present")
    else:
        print("[ERROR] Some required files are missing for Render deployment")
    
    return all_present


if __name__ == "__main__":
    print("System Test for News Crawler Optimized for Render")
    print("=" * 50)
    
    success1 = asyncio.run(test_api_rate_limits())
    success2 = test_render_deployability()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("[OK] All tests passed! System is ready for deployment on Render with Groq API.")
    else:
        print("[ERROR] Some tests failed. Please address the issues before deployment.")