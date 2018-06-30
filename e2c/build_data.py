
import yaml
import sys
import tensorflow as tf
import random
from collections import Counter
from tqdm import tqdm
import os.path

from .util import *
from .args import *



def build_vocab(args):

	hits = Counter()

	def add_lines(lines):
		for line in lines:
			line = line.replace("\n", "")

			for word in line.split(' '):
				if word != "" and word != " ":
					hits[word] += 1

	for i in ["all"]:
		for j in ["src", "tgt"]:
			with tf.gfile.GFile(args[f"{i}_{j}_path"]) as in_file:
				add_lines(in_file.readlines())

	tokens = list()
	tokens.extend(special_tokens)

	for i in string.ascii_lowercase:
		tokens.append("<"+i+">")
		tokens.append("<"+i.upper()+">")

	for i, c in hits.most_common(args["vocab_size"]):
		if len(tokens) == args["vocab_size"]:
			break

		if i not in tokens:
			tokens.append(i)

	assert len(tokens) <= args["vocab_size"]

	with tf.gfile.GFile(args["vocab_path"], 'w') as out_file:
		for i in tokens:
			out_file.write(i + "\n")

	return tokens


def load_vocab_set(args):
	tokens = list()

	with tf.gfile.GFile(args["vocab_path"]) as file:
		for line in file.readlines():
			tokens.append(line.replace("\n", ""))

	return tokens


def extract_all_translation_pairs(args):
	with tf.gfile.GFile(args["gqa_path"], 'r') as in_file:
		d = yaml.safe_load_all(in_file)

		suffixes = ["src", "tgt"]
		prefixes = args["modes"]

		with tf.gfile.GFile(args["all_src_path"], "w") as src_file:
			with tf.gfile.GFile(args["all_tgt_path"], "w") as tgt_file:
				for i in tqdm(d):
					if i["question"] and i["question"]["cypher"] is not None:
						src_file.write(pretokenize_english(i["question"]["english"]) + "\n")
						tgt_file.write(pretokenize_cypher(i["question"]["cypher"]) + "\n")



def expand_unknowns_and_partition(args, tokens):
	
	suffixes = ["src", "tgt"]
	prefixes = args["modes"]

	in_files = [tf.gfile.GFile(args[f"all_{suffix}_path"]) for suffix in suffixes]
	lines = zip(*[i.readlines() for i in in_files])

	files = {k:{} for k in prefixes}

	for i in prefixes:
		for j in suffixes:
			files[i][j] = tf.gfile.GFile(args[f"{i}_{j}_path"], "w")


	for line in tqdm(lines):
		r = random.random()

		if r < args["eval_holdback"]:
			mode = "eval"
		elif r < args["eval_holdback"] + args["predict_holdback"]:
			mode = "predict"
		else:
			mode = "train"

		for idx, suffix in enumerate(suffixes):
			in_line = line[idx].replace("\n","")
			out_line = expand_unknown_vocab(in_line, tokens) + "\n"

			files[mode][suffix].write(out_line)

	for i in in_files:
		i.close()

	for i in files.values():
		for file in i.values():
			file.close()




def etl(args):

	if not args["skip_extract"]:
		extract_all_translation_pairs(args)
	
	tokens = build_vocab(args)
	expand_unknowns_and_partition(args, tokens)


		


if __name__ == "__main__":

	def extras(parser):
		parser.add_argument('--skip-extract', action='store_true')
		parser.add_argument('--gqa_path', type=str, default="./data/gqa.yaml")

	args = get_args(extras)

	etl(args)




