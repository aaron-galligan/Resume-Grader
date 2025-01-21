    To create a new environment: python -m venv envnamehere
    To activate the environment: envnamehere\Scripts\activate
    To deactivate the environment: deactivate
    To delete an environment: rm -rf envnamehere
    To create requirements.txt: pip freeze > requirements.txt
    To list all environments: conda env list
    To clone an environment: conda create --name newenv --clone existingenv
    To export environment: conda env export > environment.yml
    To create from environment.yml: conda env create -f environment.yml
    To update environment: conda env update -f environment.yml
    To rename environment: conda rename -n oldname newname
    To install the dependencies: pip install -r requirements.txt


    Commands to run to ensure gcloud connection

    gcloud auth application-default login

    #this next one just verifys
    gcloud auth application-default print-access-token
