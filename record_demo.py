import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            record_video_dir="/Users/princegupta/.gemini/antigravity-ide/brain/412968dd-f8e3-4210-9ba7-9cad3f69f03e/scratch",
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        print("Navigating to localhost:8000")
        await page.goto("http://localhost:8000")
        
        # 1. Catalog Explorer (30s)
        print("Showing Catalog...")
        await page.wait_for_selector("#products-tbody tr:not(.loading-cell)", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Slow scroll through catalog
        for _ in range(3):
            await page.mouse.wheel(0, 500)
            await page.wait_for_timeout(2000)
        for _ in range(3):
            await page.mouse.wheel(0, -500)
            await page.wait_for_timeout(2000)
            
        # Search functionality
        print("Demonstrating Search...")
        search_input = page.locator("#catalog-search")
        await search_input.fill("Frigidaire")
        await page.wait_for_timeout(4000)
        await search_input.fill("")
        await page.wait_for_timeout(3000)

        # 2. Product Details Drawer (30s)
        print("Opening Product Drawer...")
        try:
            await page.click("#products-tbody tr:nth-child(1)", timeout=3000)
            await page.wait_for_timeout(3000)
            
            # Scroll drawer slowly
            for _ in range(6):
                await page.mouse.wheel(0, 400)
                await page.wait_for_timeout(3000)
            for _ in range(4):
                await page.mouse.wheel(0, -600)
                await page.wait_for_timeout(2000)
                
            print("Closing drawer...")
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print("Error in drawer:", e)

        # 3. Ingest SKU Tab (30s)
        print("Navigating to Ingest SKU...")
        try:
            await page.click("#nav-ingest-btn", timeout=3000, force=True)
            await page.wait_for_timeout(4000)
            
            # Fill form
            await page.fill("#inp-mpn", "LFXS26596S", timeout=5000)
            await page.wait_for_timeout(1000)
            await page.fill("#inp-manuf", "LG Electronics")
            await page.wait_for_timeout(1000)
            await page.fill("#inp-brand", "LG")
            await page.wait_for_timeout(3000)
            
            # Click batch button to show activity log
            print("Testing preset ingestion...")
            await page.click("#btn-batch-50", timeout=3000)
            await page.wait_for_timeout(8000)
            
            # Scroll console
            await page.mouse.wheel(0, 500)
            await page.wait_for_timeout(4000)
            
        except Exception as e:
            print("Error in Ingest tab:", e)

        # 4. HITL Review Queue (30s)
        print("Navigating to HITL Queue...")
        try:
            await page.click("#nav-hitl-btn", timeout=3000, force=True)
            await page.wait_for_timeout(5000)
            
            # Scroll HITL table
            for _ in range(2):
                await page.mouse.wheel(0, 400)
                await page.wait_for_timeout(3000)
                
            # If there's an action button, try to click it
            try:
                await page.click("#hitl-tbody tr:nth-child(1) button.btn-primary", timeout=3000)
                await page.wait_for_timeout(4000)
            except Exception:
                pass
                
        except Exception as e:
            print("Error in HITL tab:", e)

        # Wait a bit before ending to buffer
        await page.wait_for_timeout(3000)
        print("Done recording. Closing context.")
        await context.close()
        await browser.close()

asyncio.run(run())
