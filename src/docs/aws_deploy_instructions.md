### To Create An Instance

aws ec2 run-instances --image-id ami-0d73480446600f555 --instance-type m5a.large --key-name vockey > instance.json

##To Copy Files

aws ec2 authorize-security-group-ingress --group-name default --protocol tcp --port 22 --cidr 0.0.0.0/0

mkdir lab-3 

scp -i aws/labsuser.pem -r src/ data/catalog_data/catalog.csv ubuntu@ec2-54-167-21-148.compute-1.amazonaws.com:~/lab-3

### To Get Public DNS:
aws ec2 describe-instances --instance-id i-0895c2aa9d7a32ab3

### To Open The Required Port:
chmod 400 labuser.pem


aws ec2 authorize-security-group-ingress --group-name default --protocol tcp --port 8081 --cidr 0.0.0.0/0


###To Run The Processes
#### SSH:
`ssh -i labsuser.pem ubuntu@ec2-54-91-211-32.compute-1.amazonaws.com`

`Follow The Steps mentioned in run_instructions.md`




