#!/bin/sh

python hw1.py --file="GRCh38_latest_genomic.fna" \
              --target="NC_000006.12" \
              --start=100000 \
              --end=1200000 \
              --model="mm" \
            #   --num_state=2 \
            #   --num_symbol=4 \
            #   --num_iter=100 \
            #   --test \
            #   --test_target="NC_000007.14"