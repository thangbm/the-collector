services:
    app:
        build: .
        ports:
        - "8080:8080"
        environment:
        - NODE_ENV=production
        volumes:
        - .:/usr/src/app
        command: npm start