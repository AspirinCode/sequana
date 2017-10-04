BootStrap: debootstrap
DistType "debian"
MirrorURL: http://us.archive.ubuntu.com/ubuntu/
OSVersion: xenial

%labels

    AUTHOR Thomas Cokelaer

%post

    apt-get install -y wget
    apt-get install -y bzip2
    apt-get install -y vim
    apt-get install -y libgl1-mesa-glx  # will be required by pyqt
    apt-get install -y fontconfig # for sequanix/qt fonts otherwise no text in menus

    # for fastqc
    apt-get install -y libxrender1
    apt-get install -y libxtst6
    apt-get install -y libxi6

    # for sequanix (Qt plugin) otherwise libxcb missing
    apt-get install -y libsm-dev
    apt-get install -y libxcomposite-dev

    # This is a large data set again. When using the container a sroot, sequanix
    # looks good but in normal mode, the menu is blank...and this seems to solve
    # the issue
    apt-get install -y libgnomeui-0

    # install anaconda
    if [ ! -d /usr/local/anaconda ]; then
        #wget https://repo.continuum.io/miniconda/Miniconda3-4.3.14-Linux-x86_64.sh\
        # for now, we use 4.2.12 to have python3.5 by default so no need to
        # create a new env saving space in the process. The reason for using 3.5
        # is inherent to the packages used at the moment.
        wget https://repo.continuum.io/miniconda/Miniconda3-4.2.12-Linux-x86_64.sh\
           -O ~/anaconda.sh && \
        bash ~/anaconda.sh -b -p /usr/local/anaconda && \
        rm ~/anaconda.sh
    fi

    # set anaconda path
    export PATH=$PATH:/usr/local/anaconda/bin
    conda update conda


    conda config --add channels r
    conda config --add channels defaults
    conda config --add channels conda-forge
    conda config --add channels bioconda

    # The main packages for sequana:
    conda install --file https://raw.githubusercontent.com/sequana/sequana/master/requirements.txt

    # external tools
    conda install -y bwa fastqc kraken krona cutadapt
    conda install -y bowtie bowtie2 star subread
    conda install -y bcftools bedtools khmer samtools pigz bleach
    conda install -y picard shustring
    conda install -y snpeff freebayes spades sambamba

    # Let us save some space
    conda clean --packages -y

    #conda install -y canu busco==3.0.2 prokka # takes lots of place

    # Let us save some space
    conda clean --packages -y

    # Sequana source code
    pip install sequana==0.5.2

    conda clean --all -y # next requires lots of space
    rm -rf /usr/local/anaconda/pkgs

    # pysam/bzip/hstlib is tricky. We pin versions as follows
    conda install --override-channels -c conda-forge bzip2
    conda install --override-channels -c bioconda -c conda-forge htslib==1.5.0 
    conda install pysam==0.12.0.1

    if [ ! -d /data ]; then mkdir /data; fi
    if [ ! -d /scripts ]; then mkdir /scripts; fi
    if [ ! -d /scratch ]; then mkdir /scratch; fi
    if [ ! -d /mounting ]; then mkdir /mounting; fi
    if [ ! -d /pasteur ]; then mkdir /pasteur; fi

%environment
    export PATH=$PATH:/usr/local/anaconda/bin
    export LANG=C   # prevents perl for raising warnings
    export PERL5LIB=/usr/local/anaconda/lib/perl5/5.22.0
    echo "backend:agg" > matplotlibrc

