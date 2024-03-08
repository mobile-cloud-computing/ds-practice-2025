import axios, { AxiosInstance } from "axios";

export interface Book {
    id: string;
    title: string;
    author: string;
    description: string;
    copies: number;
    copiesAvailable: number;
    category: string;
    image_url: string;
    price: number;
    tags: string[];
}


export interface User {
    name: string;
    contact: string;
}

export interface CreditCard {
    number: string;
    expirationDate: string;
    cvv: string;
}

export interface Item {
    name: string;
    quantity: number;
}

export interface BillingAddress {
    street: string;
    city: string;
    state: string;
    zip: string;
    country: string;
}

export interface Device {
    type: string;
    model: string;
    os: string;
}

export interface Browser {
    name: string;
    version: string;
}

export interface Checkout {
    user: User;
    creditCard: CreditCard;
    userComment: string;
    items: Item[];
    discountCode: string;
    shippingMethod: string;
    giftMessage: string;
    billingAddress: BillingAddress;
    termsAndConditionsAccepted: boolean;
    notificationPreferences: string[];
    device: Device;
    browser: Browser;
    appVersion: string;
    screenResolution: string;
    referrer: string;
    deviceLanguage: string;
}


export interface CheckoutResponse {
    orderId:        string;
    status:         string;
    suggestedBooks: Book[];
}

export class BookstoreClient {
    private readonly DEFAULT_BASEURL = 'http://localhost:8081';
    private readonly client: AxiosInstance;

    constructor(baseURL?: string) {
        this.client = axios.create({
            baseURL: baseURL ?? this.DEFAULT_BASEURL,
        });
    }

    async getBooks(): Promise<Book[]> {
        const result = await this.client.get('/books');
        return result.data;
    }

    async getBook(id: string): Promise<Book> {
        const result = await this.client.get(`/books/${id}`);
        return result.data;
    }
    
    async recommendations(browseHistory: string[]): Promise<Book[]> {
        const result = await this.client.post('/recommendations', { history: browseHistory });
        return result.data;
    }

    async checkout(checkout: Checkout): Promise<CheckoutResponse> {
        const result = await this.client.post('/checkout', checkout);
        return result.data;
    }

    async healthCheck(): Promise<void> {
        return await this.client.get('/health');
    }
}