.PHONY: clean all show

all: whelk.pdf

show: whelk.pdf
	evince -s $<

tex_garbage = *.aux *.toc *.nav *.out *.log *.snm *.vrb
clean:
	rm -f whelk.pdf $(tex_garbage)

whelk.pdf: whelk.tex
	lualatex -shell-escape $< && \
	lualatex -shell-escape $<
