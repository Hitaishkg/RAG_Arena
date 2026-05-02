import os
import json
import requests
import time
from typing import List, Dict

def download_corpus(corpus_path: str = "data/corpus.json", raw_dir: str = "data/raw") -> List[Dict]:
    """
    Reads corpus.json, downloads each PDF to data/raw/<doc_id>.pdf.
    Returns list of {doc_id, name, category, local_path, status} where
    status is "ok" or "failed:<reason>".
    Skips documents already downloaded (file exists and size > 0).
    """
    # Use DATA_DIR from env if available for base path
    # If paths are absolute or already contain data/, we might not need to prepend.
    # The task says: "No hardcoded paths — all paths derived from parameters or env vars"
    
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir, exist_ok=True)

    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    results = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}

    for i, doc in enumerate(corpus, 1):
        doc_id = doc["doc_id"]
        url = doc["url"]
        local_path = os.path.join(raw_dir, f"{doc_id}.pdf")
        
        result = {
            "doc_id": doc_id,
            "name": doc["name"],
            "category": doc["category"],
            "local_path": local_path,
            "status": "ok"
        }

        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            # Task didn't specify what to print on skip, but usually helpful
            # Results should still be appended
            results.append(result)
            continue

        print(f"[{i}/{len(corpus)}] Downloading {doc_id} ... ", end="", flush=True)
        
        try:
            # Retry once on connection error
            success = False
            for attempt in range(2):
                try:
                    response = requests.get(url, headers=headers, timeout=30, stream=True)
                    response.raise_for_status()
                    
                    with open(local_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    size_mb = os.path.getsize(local_path) / (1024 * 1024)
                    print(f" OK ({size_mb:.1f} MB)")
                    success = True
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt == 0:
                        time.sleep(1)
                        continue
                    else:
                        raise e
            
            if not success:
                # This part shouldn't really be reached due to raise e above, 
                # but for completeness:
                result["status"] = "failed:unknown"
                
        except Exception as e:
            status = f"failed:{str(e)}"
            print(f" FAILED ({str(e)})")
            result["status"] = status
            if os.path.exists(local_path):
                os.remove(local_path)

        results.append(result)

    return results
